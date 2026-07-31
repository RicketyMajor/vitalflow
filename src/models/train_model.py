"""The surge-alert model: rank each facility's weeks by the risk of exceeding its own p90.

**What ships is `DEPLOYED_FEATURES` -- six columns and one classifier.** The three-stage design
this module was written against (national wave -> factor allocation -> classifier) is all here and
all measured, but the ablation in `demo()` found Stages 1 and 2 contribute under 0.01 recall to the
alert list: the national anomaly is by construction the mean of the very `z` values the classifier
already holds per facility. They are kept for reporting and as the record of that measurement.

Read `demo()` output top to bottom -- it is the argument for every choice below.

Seven things cost real work to learn and must not be undone:

* **`onset_recall` is the headline, not `recall`.** The aggregate surge metric is 52-64%
  *continuation* of a surge already under way, which a shift coordinator can see from the waiting
  room. A one-line rule -- alert iff the facility is already above its own p90 -- beats what ships
  on recall, precision AND lift in 2025 and in the sealed 2026, at equal or lower spend, while
  scoring 0.000 on onsets at h=1 because it cannot flag a surge that has not begun. Split the
  truth set and the model wins where it counts: ~2x the calendar's new surges at matched spend.
  Scoring the trivial baseline is what exposed this; `demo()` now asserts it. See docs/ §9.1b.
* **Two significant figures, never three.** The fit is bit-reproducible across processes since
  2026-07-30 (the `ORDER BY` in `load_weekly_target` -- delete it and nothing here reproduces),
  but it stays *sensitive*: permuting the panel's row order, same data and same seed, moves 2026
  h=1 lift across 7.94-8.31 and onset recall across 0.191-0.221. A hard threshold on 274 surges
  in 4,984 rows amplifies last-bit differences that are invisible in the scores. Every AC holds
  across that envelope; a "5 of 6 cells" claim that rested on 0.002 did not. See docs/ §9.3.
* **Scored within season, never pooled.** A pooled R2 across seasons rewards a model for
  predicting differences *between* seasons, which no hospital needs a model for. It nearly
  produced a false positive in `03e` -- see context/handoff/handoff-007-virology-and-scope.md.
* **The climatology is a fitted object.** `03e` measured 0.835 / 0.598 with a climatology and a
  per-facility scale estimated over every year, including the test season. Spec AC4 forbids that,
  so `leak_free=True` (the default) refits both on training years only, once per test season.
  The deployable Stage 1 baseline is 0.772 / 0.450; `demo()` prints both.
* **An R2 gain that does not re-order the alert list is not a result.** Stage 1's oracle variant
  produces the same alert list as its forecast despite an R2 of 0.772.
* **A benchmark must come from this module's own scorer.** `03d` reported 0.321 / 0.428 for its
  best model; the same feature composition scored by `score_alerts` gives 0.313 / 0.396.
* **Recall is only comparable at equal spend.** What ships alerts on a cut fixed before the season,
  so the budget is free to drift -- 5.1% of facility-weeks in quiet 2025, 8.2% in 2024. Compare
  those rows on `lift`, never on `recall`, or a model that merely alerts more looks like a model
  that predicts better. `prospective_alerts` and the 2026-07-28 decision-log entry.

Spec: context/specs/surge-alert-model.md · Decisions: context/decisions/log.md, 2026-07-27.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.features.build_features import (  # noqa: E402
    chord_to_arc_km, load_weekly_target, to_xyz,
)

Y = "Total_Respiratorias"
BASE_YEAR = 2015
COVID_YEARS = [2020, 2021]   # AC6: excluded, not flagged -- a 75% collapse is a different process
TEST_SEASONS = [2017, 2018, 2019, 2022, 2023, 2024, 2025]
HORIZONS = (1, 2)            # the wall is at three weeks; h >= 4 only as a negative control
MIN_TRAIN_WEEKS = 60

FEATURES = ["er", "er_l1", "er_l2", "er_l4", "er_d4"]


def load_panel():
    """The weekly facility panel with a continuous week index `t`, COVID years removed."""
    p = load_weekly_target(BASE_YEAR, 2026)
    p = p[~p["Anio"].isin(COVID_YEARS)].copy()
    p["t"] = (p["Anio"] - BASE_YEAR) * 52 + p["SemanaEstadistica"] - 1
    return p


KEYS = ["EstablecimientoCodigo", "SemanaEstadistica"]


def standardize(panel, fit_years=None):
    """Attach each facility's climatology, scale and standardized anomaly `z`.

    `fit_years` restricts both fitted quantities to those years; a facility with no history there
    drops out, exactly as a newly reporting facility would in deployment.
    """
    fit_rows = panel if fit_years is None else panel[panel["Anio"].isin(fit_years)]
    clim = fit_rows.groupby(KEYS)[Y].mean().rename("clim")
    scale = fit_rows.groupby("EstablecimientoCodigo")[Y].std().rename("scale")

    p = panel.join(clim, on=KEYS).join(scale, on="EstablecimientoCodigo")
    p["z"] = (p[Y] - p["clim"]) / p["scale"].replace(0, np.nan)
    return p


def national_anomaly(panel, fit_years=None):
    """The national series: cross-facility mean of standardized facility anomalies, by week `t`.

    Standardizing first means a 600-bed hospital and a rural clinic weigh the same.
    """
    p = standardize(panel, fit_years)
    d = pd.DataFrame(index=pd.RangeIndex(int(p["t"].min()), int(p["t"].max()) + 1, name="t"))
    d["er"] = p.groupby("t")["z"].mean()  # missing weeks stay NaN so .shift() never crosses a gap
    d["season"] = BASE_YEAR + d.index // 52
    d["week"] = d.index % 52 + 1
    return d


def add_lags(d):
    """Own-history features: lags 1, 2, 4 and the four-week change."""
    f = d.copy()
    for lag in (1, 2, 4):
        f[f"er_l{lag}"] = f["er"].shift(lag)
    f["er_d4"] = f["er"] - f["er"].shift(4)
    return f


def fit(train):
    # ponytail: RidgeCV on own lags is the spec's benchmark, not a placeholder. Anything more
    # elaborate has to beat 0.835 / 0.598 on this same within-season protocol before it ships.
    model = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
    return model.fit(train[FEATURES], train["y"])


def train_years_for(panel, season, since=None):
    """Seasons strictly before `season` (AC4), optionally clipped to start at `since`."""
    return [y for y in sorted(panel["Anio"].unique())
            if y < season and (since is None or y >= since)]


def national_forecast(panel, season, h, leak_free=True):
    """Stage 1 out of sample: fit on seasons before `season`, predict inside it.

    Indexed by the **target** week `t + h`, so a facility-week can join its own forecast directly.
    Returns None when the season has too little history to train on.
    """
    fit_years = train_years_for(panel, season) if leak_free else None
    f = add_lags(national_anomaly(panel, fit_years=fit_years))

    f["y"] = f["er"].shift(-h)
    train = f[f["season"] < season].dropna(subset=FEATURES + ["y"])
    test = f[f["season"] == season].dropna(subset=FEATURES + ["y"])
    if len(train) < MIN_TRAIN_WEEKS or test.empty:
        return None

    return pd.DataFrame({"er_hat": fit(train).predict(test[FEATURES]),
                         "er_true": test["y"].to_numpy()},
                        index=pd.Index(test.index + h, name="t"))


def backtest(panel, h, leak_free=True):
    """Expanding window, one test season at a time. Returns out-of-sample R2 per season (AC3/AC4).

    With `leak_free`, the climatology and per-facility scale behind the target are refitted for
    each test season on strictly earlier years. Otherwise they are fitted once over all years,
    which is what `03e` did and what AC4 forbids.
    """
    per = {}
    for season in TEST_SEASONS:
        fc = national_forecast(panel, season, h, leak_free=leak_free)
        if fc is None:
            continue
        y, pred = fc["er_true"].to_numpy(), fc["er_hat"].to_numpy()
        per[season] = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    return pd.Series(per, name=f"h={h}")


SURGE_QUANTILE = 0.90   # a surge is a week above the facility's own historical p90
ALERT_SHARE = 0.10      # every model spends the same budget, or recall is won by shouting

# Product scope, 2026-07-29. The alert goes to a hospital ER's shift coordinator, who can activate
# the bed contingency plan, reassign internal functions, or authorise reinforcement shifts. An
# ambulatory SAPU/SAR runs one or two physicians per shift with no spare boxes and therefore has no
# lever -- an alert there is noise. So a metric averaged over all 623 facilities is not measuring the
# product: 446 of them cannot act on it. See context/decisions/log.md, 2026-07-29.
HOSPITAL_ER = "UEH"

# The winter reinforcement budget is released on a MINSAL decree, typically late May / June, so a
# wider alert set is only *actionable* inside the campaign; outside it the hospital is on the fixed
# dotación approved the month before and extra shifts cannot be bought. Hence two budget regimes.
# The weeks come from the calendar and are NEVER fitted -- tuning the boundary on outcomes would be
# exactly the leak AC4 exists to prevent.
CAMPAIGN_WEEKS = range(22, 36)
CAMPAIGN_SHARE = 0.20


def hospital_er_facilities(panel):
    """Facility codes whose emergency department belongs to a hospital -- the product's scope.

    Matched case-insensitively on `TipoUrgencia`, which is the authoritative column: three
    facilities are `TipoEstablecimiento == "Hospital"` without being UEH, and `normalize_category`
    preserves case deliberately, so both "Urgencia ambulatoria (SAR)" and "Urgencia Ambulatoria
    (SAR)" occur in the raw data.
    """
    t = panel.groupby("EstablecimientoCodigo")["TipoUrgencia"].first().astype(str)
    return t.index[t.str.contains(HOSPITAL_ER, case=False, na=False)]


def high_complexity_facilities(panel):
    """The subset of hospital ERs with resuscitation capacity -- 55 units, 12.3% of volume."""
    c = panel.groupby("EstablecimientoCodigo")["NivelComplejidad"].first().astype(str)
    return c.index.intersection(hospital_er_facilities(panel)).intersection(
        c.index[c.str.contains("alta", case=False, na=False)])


def scope_panel(panel, facilities=None):
    """Restrict the panel to `facilities`, or return it whole.

    Filtering the panel and filtering the scored rows are equivalent **for what ships**: every one
    of the six `DEPLOYED_FEATURES` is derived from that facility's own history, so no deployed
    feature changes when other facilities leave. It does change Stage 1 and `beta`, which is why
    the Stage 1/2 tables and the ablation stay on the full panel.
    """
    if facilities is None:
        return panel
    return panel[panel["EstablecimientoCodigo"].isin(facilities)].copy()


def two_regime_cuts(cal, score, base=ALERT_SHARE, campaign=CAMPAIGN_SHARE):
    """One score cut per budget regime, both fixed on the calibration season (AC4).

    Returns `{True: campaign_cut, False: base_cut}`, keyed by whether the target week falls inside
    `CAMPAIGN_WEEKS`. Each regime's cut is the quantile of *that regime's own* calibration weeks:
    a single national quantile would let the busy campaign weeks set the threshold for the quiet
    ones, which is the confound this rule exists to remove.
    """
    s = pd.Series(np.asarray(score), index=cal.index)
    inside = cal["week"].isin(CAMPAIGN_WEEKS)
    return {True: s[inside].quantile(1 - campaign),
            False: s[~inside].quantile(1 - base)}

# Stage 3 must beat this. Measured below, post-COVID window (see BASELINE_TRAIN_FROM), by the same
# `score_alerts` that will score Stage 3 -- a benchmark computed by other code is not a benchmark.
BASELINE_TRAIN_FROM = 2022
AC2_BASELINE = {2025: {"recall": 0.232, "precision": 0.184},
                2024: {"recall": 0.252, "precision": 0.351}}


def alert_flags(test, pred, thresholds=None):
    """Which facility-weeks get an alert.

    Default: the top `ALERT_SHARE` of each facility's own weeks, ranked by `pred`. This needs the
    whole test season at once, which deployment does not have -- pass `thresholds` from
    `calibrate_thresholds` for the prospective rule instead.
    """
    facility = test["EstablecimientoCodigo"]
    pred = pd.Series(np.asarray(pred), index=test.index)

    if isinstance(thresholds, dict):
        # Two-regime: the cut depends on the target week's calendar position, not on the facility.
        return pred >= test["week"].isin(CAMPAIGN_WEEKS).map(thresholds)

    if thresholds is not None:
        per_facility, national = thresholds
        return pred >= facility.map(per_facility).fillna(national)

    rank = pred.groupby(facility).rank(ascending=False, method="first")
    return rank <= facility.map(facility.value_counts()) * ALERT_SHARE


def calibrate_thresholds(cal, score, share=ALERT_SHARE):
    """The score cut that spent exactly `share` of the *calibration* season's weeks.

    Returns `(per_facility, national)`; the national quantile covers facilities the calibration
    season never saw. `cal` must be a season predicted out of sample -- an in-sample fit puts the
    probabilities too high and the threshold with them.
    """
    s = pd.Series(np.asarray(score), index=cal.index)
    return (s.groupby(cal["EstablecimientoCodigo"]).quantile(1 - share), s.quantile(1 - share))


def onset_scores(test, alert, truth):
    """Recall split by whether the surge is NEW. `onset_recall` is the primary metric since
    2026-07-29; everything else in `score_alerts` is mostly the easy half.

    Returns NaN when the caller built its own frame without the `onset` column -- only
    `climatology_alerts` does, and it is scored on the aggregate by design.
    """
    if "onset" not in test:
        return {"onset_recall": float("nan"), "contin_recall": float("nan"), "onsets": 0}

    onset = test["onset"]                     # already ANDed with `surge` in alert_frame
    contin = truth & ~onset
    return {"onset_recall": int((alert & onset).sum()) / max(int(onset.sum()), 1),
            "contin_recall": int((alert & contin).sum()) / max(int(contin.sum()), 1),
            "onsets": int(onset.sum())}


def score_alerts(test, pred, thresholds=None):
    """Recall/precision at a fixed alert budget: each facility alerts its own top 10% of weeks.

    `pred` ranks the facility's weeks; only the ordering matters, not the units. `test` supplies
    the boolean `surge` column. An R2 gain that does not re-order this list is not a result.

    With `thresholds` the budget is a cut fixed before the season, so the spend is whatever the
    season turns out to deserve; `share` reports what it actually came to.

    **Read `onset_recall`, not `recall`, as the headline (2026-07-29).** `recall` counts surge
    continuation, which is 52-64% of the truth set and needs no model -- a one-line persistence
    rule beats what ships on `recall`, `precision` and `lift` while scoring 0.000 on onsets at
    h=1. That is a fact about this metric, not about the model. `docs/` §9.1b and rule 18.
    """
    alert, truth = alert_flags(test, pred, thresholds), test["surge"]

    tp = int((alert & truth).sum())
    precision = tp / max(int(alert.sum()), 1)
    base_rate = int(truth.sum()) / max(len(test), 1)
    return {
        "recall": tp / max(int(truth.sum()), 1),
        "precision": precision,
        "alerts": int(alert.sum()),
        "surges": int(truth.sum()),
        # A prospective cut does not spend exactly ALERT_SHARE -- the season spends what it
        # deserves. So recall alone stops being comparable between rules, and `lift` (how many
        # times better than alerting at random) is what survives a change of budget.
        "share": int(alert.sum()) / max(len(test), 1),
        "lift": precision / max(base_rate, 1e-9),
        "silent": int((~alert.groupby(test["EstablecimientoCodigo"]).any()).sum()),
        **onset_scores(test, alert, truth),
    }


def matched_spend(test, scores, n):
    """Score every rule in `scores` at the SAME alert count `n`, ranked top-N.

    **The only fair way to compare onset recall.** At each rule's own natural spend the
    climatology appears to beat what ships on 2026 onsets, 0.305 against 0.191 -- purely because
    it fires 533 alerts against 294. At matched budget it reverses to 0.137 against 0.206. Rule 5
    ("compare only at matched spend") caught that, and it caught it twice in one session.
    """
    out = {}
    for label, s in scores.items():
        rank = pd.Series(np.asarray(s, dtype=float), index=test.index).rank(
            ascending=False, method="first")
        # Fed back through score_alerts as a 0/1 score cut at 0.5, so the metrics come from one
        # implementation rather than a second copy that can drift from it.
        out[label] = score_alerts(test, (rank <= n).astype(float),
                                  (pd.Series(dtype=float), 0.5))
    return out


def climatology_alerts(panel, test_year, train_from=None):
    """The baseline Stage 3 must beat: rank each facility's weeks by its own climatology.

    Climatology, per-facility scale and the p90 surge threshold all come from training years only
    (AC4). `train_from` clips how far back the history reaches -- `03d` used 2022, giving a two-
    to three-year climatology; deployment will always have the full record.
    """
    keys = ["EstablecimientoCodigo", "SemanaEstadistica"]
    train_years = [y for y in sorted(panel["Anio"].unique())
                   if y < test_year and (train_from is None or y >= train_from)]
    train = panel[panel["Anio"].isin(train_years)]

    clim = train.groupby(keys)[Y].mean().rename("clim")
    thr = train.groupby("EstablecimientoCodigo")[Y].quantile(SURGE_QUANTILE).rename("thr")

    test = (panel[panel["Anio"] == test_year]
            .join(clim, on=keys)
            .join(thr, on="EstablecimientoCodigo")
            .dropna(subset=["clim", "thr"]))
    test["surge"] = test[Y] > test["thr"]
    # ponytail: no horizon argument -- the climatology of week w is the same object however far
    # ahead it is read, so its ranking (and therefore its recall) is identical at h=1 and h=2.
    out = score_alerts(test, test["clim"])
    out["train_years"] = len(train_years)
    out["facilities"] = test["EstablecimientoCodigo"].nunique()
    return out


SHRINK_WEEKS = 52   # ponytail: a facility with one year on record lands halfway to the panel
                    # mean. Tune if short-history facilities turn out to be the weak spot.


def facility_loadings(panel, season, shrink=SHRINK_WEEKS):
    """`beta[i]`: how strongly facility i's own anomaly moves with the national one.

    cov(z_i, er) / var(er) over training years, shrunk toward the panel mean by history length --
    a facility with thirty weeks on record cannot support its own loading. Measured against the
    same national series `national_forecast` predicts, or the loading refers to a different object.
    """
    fit_years = train_years_for(panel, season)
    p = standardize(panel, fit_years)
    nat = national_anomaly(panel, fit_years)["er"]

    tr = p[p["Anio"].isin(fit_years)][["EstablecimientoCodigo", "t", "z"]].copy()
    tr["er"] = tr["t"].map(nat)
    tr["ze"] = tr["z"] * tr["er"]
    tr = tr.dropna(subset=["z", "er"])

    g = tr.groupby("EstablecimientoCodigo")
    m, var, n = g[["z", "er", "ze"]].mean(), g["er"].var(ddof=0), g.size()
    beta = ((m["ze"] - m["z"] * m["er"]) / var.replace(0, np.nan)).dropna()

    n = n.reindex(beta.index)
    return ((n * beta + shrink * beta.mean()) / (n + shrink)).rename("beta")


def stage2_alerts(panel, test_year, h, clim_from=BASELINE_TRAIN_FROM, oracle=False):
    """Stage 2: `clim[i, w] + beta[i] * scale[i] * national_hat[w]`, ranked into alerts.

    Returns Stage 2 and the climatology baseline scored on **identical rows against an identical
    truth set**, so the only difference between them is the added national term. The threshold
    always comes from the AC2 window; `clim_from` varies only the ranking climatology.

    `oracle` substitutes the realised national anomaly for the forecast. It is not deployable --
    it is the control that separates "the allocation is wrong" from "Stage 1 missed that season".
    """
    fc = national_forecast(panel, test_year, h)
    if fc is None:
        return None

    beta = facility_loadings(panel, test_year)
    rank_rows = panel[panel["Anio"].isin(train_years_for(panel, test_year, since=clim_from))]
    thr_rows = panel[panel["Anio"].isin(train_years_for(panel, test_year,
                                                        since=BASELINE_TRAIN_FROM))]

    test = (panel[panel["Anio"] == test_year]
            .join(rank_rows.groupby(KEYS)[Y].mean().rename("clim"), on=KEYS)
            .join(rank_rows.groupby("EstablecimientoCodigo")[Y].std().rename("scale"),
                  on="EstablecimientoCodigo")
            .join(thr_rows.groupby("EstablecimientoCodigo")[Y].quantile(SURGE_QUANTILE)
                  .rename("thr"), on="EstablecimientoCodigo")
            .join(beta, on="EstablecimientoCodigo"))
    test["er_hat"] = test["t"].map(fc["er_true" if oracle else "er_hat"])
    test = test.dropna(subset=["clim", "scale", "thr", "beta", "er_hat"])
    test["surge"] = test[Y] > test["thr"]

    return {"stage 2": score_alerts(test, test["clim"] + test["beta"] * test["scale"] * test["er_hat"]),
            "climatology": score_alerts(test, test["clim"])}


STATIC = ["TipoEstablecimiento", "NivelComplejidad", "RegionGlosa"]
# ponytail: the ranking is *within* facility, so anything constant per facility (static metadata,
# beta, scale) cannot re-order a facility's own weeks on its own. They stay because their
# interactions with the time-varying features can -- "trust the national term more at a big
# hospital". If a feature-importance pass shows they earn nothing, delete them.
STAGE3_FEATURES = ["z", "z_l1", "z_l2", "z_d4", "clim_z", "stage2_z",
                   "er", "er_hat", "week", "beta", "scale"] + STATIC

# What actually ships. The ablation in `demo()` is the argument: no other feature group -- the
# national wave, the Stage 2 allocation, neighbour rings, static metadata -- moves recall by more
# than 0.01. Six columns, one classifier, one panel, nothing else to refresh weekly.
DEPLOYED_FEATURES = ["z", "z_l1", "z_l2", "z_d4", "clim_z", "week"]

RINGS = [(0, 25), (25, 100), (100, 400)]   # km bands, as in `03d`
RING_FEATURES = [f"ring_{lo}_{hi}" for lo, hi in RINGS]


def ring_means(Z, facilities):
    """Mean neighbour anomaly in each distance band at week `t`, observable at `t`.

    Carried so `03d`'s best model can be reproduced through this module's scorer. `03d` concluded
    neighbours do not lead; this reproduces its features, it does not reopen that finding.
    """
    xyz = to_xyz(facilities["Latitud"], facilities["Longitud"])
    D = chord_to_arc_km(np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1))
    np.fill_diagonal(D, np.inf)            # a facility is never its own neighbour

    Zv = Z.to_numpy()
    seen = np.isfinite(Zv).astype(float)
    out = {}
    for (lo, hi), name in zip(RINGS, RING_FEATURES):
        M = ((D >= lo) & (D < hi)).astype(float)
        den = seen @ M.T                   # neighbours actually reporting that week
        out[name] = pd.DataFrame(np.where(den > 0, (np.nan_to_num(Zv) @ M.T) / np.maximum(den, 1),
                                          np.nan), index=Z.index, columns=Z.columns)
    return out


def alert_frame(panel, test_year, h, clim_from=BASELINE_TRAIN_FROM):
    """Facility-week rows: features known at origin week `t`, surge label at target week `t + h`.

    Returns `(train, test)`. Everything fitted -- climatology, scale, p90 threshold, `beta`, the
    Stage 1 model -- comes from seasons before `test_year` (AC4), and the national forecast is
    out-of-sample in the *training* rows too: each training season is forecast by a Stage 1 fitted
    on seasons before it, so the classifier never sees a national term better than the one it will
    get in deployment.

    Training rows start at `BASELINE_TRAIN_FROM`. Pre-COVID seasons carry a different demand level,
    and a p90 threshold fitted post-COVID would label almost none of their weeks a surge.
    """
    train_seasons = train_years_for(panel, test_year, since=BASELINE_TRAIN_FROM)
    rank_rows = panel[panel["Anio"].isin(train_years_for(panel, test_year, since=clim_from))]
    p = standardize(panel, rank_rows["Anio"].unique())

    per_fac = rank_rows.groupby("EstablecimientoCodigo")[Y]
    level, thr = per_fac.mean(), per_fac.quantile(SURGE_QUANTILE)
    scale = p.groupby("EstablecimientoCodigo")["scale"].first()

    full_t = range(int(panel["t"].min()), int(panel["t"].max()) + 1)
    def wide(col):
        return p.pivot_table(index="t", columns="EstablecimientoCodigo", values=col).reindex(full_t)

    Z, C, L = wide("z"), wide("clim"), wide(Y)
    coords = panel.groupby("EstablecimientoCodigo")[["Latitud", "Longitud"]].first().loc[Z.columns]
    frames = {"z": Z, "z_l1": Z.shift(1), "z_l2": Z.shift(2), "z_d4": Z - Z.shift(4),
              "clim_fut": C.shift(-h), "lvl_fut": L.shift(-h),
              # For the onset split and the persistence baseline, both added 2026-07-29. `lvl_now`
              # is the origin week; `lvl_prev` is the week before the TARGET week, which is the
              # origin week itself when h=1.
              "lvl_now": L, "lvl_prev": L.shift(-(h - 1)), **ring_means(Z, coords)}
    long = pd.concat({k: v.stack(future_stack=True) for k, v in frames.items()}, axis=1)
    long.index.names = ["t", "EstablecimientoCodigo"]
    long = long.reset_index()

    nat = national_anomaly(panel, fit_years=train_years_for(panel, test_year))["er"]
    parts = [national_forecast(panel, s, h) for s in train_seasons + [test_year]]
    fc = pd.concat([f for f in parts if f is not None])

    fac = long["EstablecimientoCodigo"]
    target_t = long["t"] + h
    long["er"] = long["t"].map(nat)
    long["er_hat"] = target_t.map(fc["er_hat"])
    long["week"] = target_t % 52 + 1
    long["target_season"] = BASE_YEAR + target_t // 52
    long["beta"] = fac.map(facility_loadings(panel, test_year))
    long["scale"] = fac.map(scale)
    long["thr"] = fac.map(thr)
    long["clim_z"] = (long["clim_fut"] - fac.map(level)) / long["scale"]
    long["stage2_z"] = long["beta"] * long["er_hat"]
    long["surge"] = long["lvl_fut"] > long["thr"]

    # Onset vs continuation, 2026-07-29. `surge` is 52-64% continuation of a surge already under
    # way, and a shift coordinator sees that from the waiting room -- so the aggregate metric is
    # mostly the half that needs no model. `onset` is the half that does. See docs/ §9.1b.
    # `surge_now` is the persistence baseline in a single column: "alert iff above p90 already".
    # Deliberately NOT added to the dropna below -- doing so would change every row count this
    # project has published. A missing previous week therefore reads as "not in surge", which is
    # the same treatment the scratch measurement used, so the recorded figures stay comparable.
    long["surge_now"] = long["lvl_now"] > long["thr"]
    long["onset"] = long["surge"] & ~(long["lvl_prev"] > long["thr"])

    static = panel.groupby("EstablecimientoCodigo")[STATIC].first()
    for col in STATIC:
        # normalize_category leaves pd.NA for placeholders; sklearn's encoder rejects a mixed
        # NAType/str column, and "unknown" is a real category here -- DEIS leaves fields blank.
        long[col] = fac.map(static[col]).astype(object).fillna("unknown").astype("category")

    long = long.dropna(subset=[c for c in STAGE3_FEATURES if c not in STATIC] + ["lvl_fut", "thr"])
    return (long[long["target_season"].isin(train_seasons)],
            long[long["target_season"] == test_year])


def stage3_predict(panel, test_year, h, clim_from=BASELINE_TRAIN_FROM, features=DEPLOYED_FEATURES):
    """Fit the surge classifier on training seasons, return the test rows with `prob` attached."""
    train, test = alert_frame(panel, test_year, h, clim_from)

    model = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, categorical_features="from_dtype", random_state=0)
    model.fit(train[features], train["surge"])

    test = test.copy()
    test["prob"] = model.predict_proba(test[features])[:, 1]
    return train, test


def stage3_alerts(panel, test_year, h, clim_from=BASELINE_TRAIN_FROM, features=DEPLOYED_FEATURES):
    """Stage 3: rank facility-weeks by P(surge). Returns all three models on identical rows."""
    train, test = stage3_predict(panel, test_year, h, clim_from, features)
    stage2 = test["clim_fut"] + test["beta"] * test["scale"] * test["er_hat"]
    return {"climatology": score_alerts(test, test["clim_fut"]),
            "stage 2": score_alerts(test, stage2),
            "stage 3": score_alerts(test, test["prob"]),
            "n_train": len(train), "n_test": len(test)}


def prospective_alerts(panel, test_year, h, features=DEPLOYED_FEATURES):
    """AC2 scored the way deployment must score it: the cut is fixed before the season starts.

    The within-year rank in `alert_flags` compares week 30 against week 45, which has not happened
    yet. Here the previous season is predicted out of sample by a model that never saw it, its
    scores give the cut, and the test season is judged against that cut -- nothing from inside the
    test season sets the budget, so the spend is free to be whatever the season deserves.

    **The rank rule was only ever unfair to Stage 3.** A climatology score is a function of
    week-of-year and training seasons alone, so it is fully known before the season opens and
    ranking it within the year leaks nothing -- the baseline's 0.231 / 0.253 stand as deployable.
    P(surge) moves with realised data, so ranking it within the year does not stand. All three
    rules are reported for both models anyway, because a cut mechanism that flattered whoever it
    was applied to would show up here as climatology gaining too.

    The baseline is scored on `clim_z`, not the raw climatology level. Within a facility the two
    rank identically, so `rank` and `per facility` are unchanged -- but a *national* cut on raw
    counts would just alert the largest hospitals every week, which is not the climatology
    baseline, it is a hospital-size baseline. A weakened baseline proves nothing.
    """
    cal = stage3_predict(panel, test_year - 1, h, features=features)[1]
    test = stage3_predict(panel, test_year, h, features=features)[1]

    out = {}
    for name, col in (("climatology", "clim_z"), ("stage 3", "prob")):
        out[name] = {
            "rank": score_alerts(test, test[col]),
            "per facility": score_alerts(test, test[col], calibrate_thresholds(cal, cal[col])),
            # One cut for the whole country: lets the budget flow to the facilities that need it
            # instead of forcing 10% of weeks onto every facility including the quiet ones.
            "national": score_alerts(test, test[col],
                                     (pd.Series(dtype=float), cal[col].quantile(1 - ALERT_SHARE))),
            # Two cuts, one per budget regime. Not shipped until measured -- rule 8.
            "two regime": score_alerts(test, test[col], two_regime_cuts(cal, cal[col])),
        }

    # The trivial baseline, added 2026-07-29 after an audit found it had never been scored: alert
    # iff the facility is ALREADY above its own p90. No training, no features, no cut to calibrate
    # -- it is a boolean, so the threshold is 0.5 and the spend is whatever the season's base rate
    # comes to. It beats what ships on recall, precision AND lift in 2025 and in the sealed 2026,
    # at equal or lower spend, and scores 0.000 on onsets at h=1 because it structurally cannot
    # flag a surge that has not begun. That contrast is the entire argument for reading
    # `onset_recall`. Rule 18: score the trivial baseline before believing a headline.
    out["persistence"] = {"fixed": score_alerts(test, test["surge_now"].astype(float),
                                                (pd.Series(dtype=float), 0.5))}
    return out


def fit_calibrator(cal):
    """Isotonic score -> observed frequency, fitted on the calibration season.

    **Measured 2026-07-29 and NOT shipped: it makes calibration worse.** Mean |gap| over score
    deciles went 0.030 -> 0.035 (2025) and 0.058 -> 0.210 (2024). Kept because `demo()` prints
    the failure, and because the reason is a property of the problem rather than of this code:

    * The surge base rate moves 7.7% (2025) to 13.3% (2024) between seasons, and *which kind of
      season it is* is the thing being forecast. A mapping learned on last season's frequencies
      is applied to a season with a different one, so it is biased by the very quantity that is
      unknown at calibration time. A prospectively calibrated absolute probability is close to
      unobtainable here.
    * The 2024 calibrator is fitted on 2023, whose model saw only 2022. One season of training
      behind one season of calibration.
    * Isotonic is monotone but not *strictly* so: flat regions collapse distinct scores into ties,
      which moved the alert set by 89 rows (2025) and 677 (2024). The claim that a monotone map
      cannot change the alert set is wrong in practice.

    The served column is therefore `score`, not `surge_probability`. What this model produces is a
    validated ranking; the absolute level depends on a season severity nobody knows in advance.
    """
    return IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(
        cal["prob"].to_numpy(), cal["surge"].to_numpy())


def reliability(prob, truth, bins=10):
    """Predicted vs observed frequency by score decile -- the calibration check itself."""
    q = pd.qcut(pd.Series(np.asarray(prob)), bins, duplicates="drop", labels=False)
    t = pd.DataFrame({"p": np.asarray(prob), "y": np.asarray(truth), "bin": q})
    g = t.groupby("bin", observed=True).agg(predicted=("p", "mean"), observed=("y", "mean"),
                                            n=("y", "size"))
    g["gap"] = g["predicted"] - g["observed"]
    return g


ALERT_LIST = ROOT / "data" / "processed" / "alert_list.parquet"


def write_alert_list(panel, test_year, horizons=HORIZONS, path=ALERT_LIST, hospital_only=True):
    """AC7: the serving interface. One row per (facility, target week, horizon).

    The `alert` flag uses the prospective national cut -- one P(surge) threshold for the country,
    fixed on the previous season before this one starts. The within-year rank it replaced cannot
    be computed in deployment at all: it needs week 45 to decide week 30. `cut` is written into
    the file so a consumer can see what the flag means and re-threshold if it wants a different
    operating point.

    The column is `score`, not `surge_probability`. It ranks; it is not a calibrated frequency,
    and calibrating it was tried and measured worse -- see `fit_calibrator`. Naming it after what
    it is stops a consumer reading 0.53 as "53% chance".

    **Hospital ERs only since 2026-07-29.** An ambulatory SAPU/SAR cannot act on an alert -- fixed
    staffing, no spare boxes -- so shipping it one is noise, and scoring the list over facilities
    that cannot act was measuring the wrong population. Measured, the restriction *improves* the
    product: recall 0.335 -> 0.464 and lift 6.63 -> 7.09 in 2025 at h=1, with silent facilities
    falling from 185 to 49. Pass `hospital_only=False` to reproduce the old national list.
    """
    panel = scope_panel(panel, hospital_er_facilities(panel) if hospital_only else None)

    out = []
    for h in horizons:
        cal = stage3_predict(panel, test_year - 1, h)[1]
        cut = cal["prob"].quantile(1 - ALERT_SHARE)
        _, test = stage3_predict(panel, test_year, h)
        out.append(pd.DataFrame({
            "facility": test["EstablecimientoCodigo"].to_numpy(),
            "year": test_year,
            "week": test["week"].to_numpy(),
            "horizon": h,
            "score": test["prob"].to_numpy(),
            "cut": cut,
            "alert": (test["prob"] >= cut).to_numpy(),
            "observed_surge": test["surge"].to_numpy(),   # blank in live use; the target week
            # Whether that surge was NEW. Carried so a consumer can score the list on the metric
            # that matters without rebuilding the panel -- see `onset_scores`.
            "observed_onset": test["onset"].to_numpy(),
        }))                                               # has not happened yet

    df = pd.concat(out, ignore_index=True).sort_values(
        ["horizon", "week", "score"], ascending=[True, True, False])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df, path


# The deployable baseline, measured leak-free by this module. AC1's 0.80 / 0.55 came from `03e`,
# which fitted the climatology on every year including the test season; that protocol is not
# reproducible in deployment and is not reachable here. These guard against regression -- they are
# not a quality bar. See context/decisions/log.md, 2026-07-27 (Stage 1 leak-free baseline).
BASELINE = {"h=1": 0.75, "h=2": 0.43}
AC1 = {"h=1": 0.80, "h=2": 0.55}


def demo():
    """Self-check: the leak-free protocol (AC4), with the leaky `03e` variant for comparison."""
    panel = load_panel()

    clean = pd.DataFrame({f"h={h}": backtest(panel, h) for h in HORIZONS})
    leaky = pd.DataFrame({f"h={h}": backtest(panel, h, leak_free=False) for h in HORIZONS})

    print("Stage 1 -- national wave, within-season out-of-sample R2 (expanding window)")
    print(f"{panel['EstablecimientoCodigo'].nunique()} facilities, "
          f"{panel['Anio'].min()}-{panel['Anio'].max()} excluding {COVID_YEARS}\n")
    print("climatology fitted on training years only (AC4):")
    print(clean.round(3).to_string())
    print(f"\n{'median':<8}" + "".join(f"{clean[c].median():>8.3f}" for c in clean))
    print(f"{'03e':<8}" + "".join(f"{leaky[c].median():>8.3f}" for c in leaky)
          + "   <- climatology fitted on all years, including test (not deployable)")

    assert list(clean.index) == TEST_SEASONS, "a test season was silently skipped"
    for col, floor in BASELINE.items():
        got = clean[col].median()
        assert got >= floor, f"regression at {col}: median R2 {got:.3f} < {floor}"

    print()
    for col, target in AC1.items():
        got = clean[col].median()
        verdict = "meets" if got >= target else "BELOW"
        print(f"{verdict:>6} AC1 at {col}: {got:.3f} vs {target} required")

    print("\n\nAC2 baseline -- climatology alert recall at a 10% budget, fitted on training years")
    print(f"{'test':<6}{'history':<24}{'yrs':>4}{'recall':>9}{'precision':>11}{'alerts':>9}{'surges':>9}")
    for test_year in AC2_BASELINE:
        for label, train_from in ((f"post-COVID (>={BASELINE_TRAIN_FROM})", BASELINE_TRAIN_FROM),
                                  ("full record", None)):
            r = climatology_alerts(panel, test_year, train_from=train_from)
            print(f"{test_year:<6}{label:<24}{r['train_years']:>4}{r['recall']:>9.3f}"
                  f"{r['precision']:>11.3f}{r['alerts']:>9,}{r['surges']:>9,}")

    # Pre-COVID seasons describe a seasonal shape that no longer holds, so they weaken the
    # ranking: 2024 lift (precision / base rate) falls 2.63 -> 1.92 when they are included. The
    # benchmark uses the window that makes climatology strongest -- beating a weak baseline
    # proves nothing. Note this is the opposite of Stage 1, where full history wins.
    for test_year, want in AC2_BASELINE.items():
        got = climatology_alerts(panel, test_year, train_from=BASELINE_TRAIN_FROM)
        for metric, value in want.items():
            assert abs(got[metric] - value) < 0.01, \
                f"AC2 baseline drifted, {test_year} {metric}: {got[metric]:.3f} vs {value}"

    print("\n\nStage 2 -- clim[i,w] + beta[i]*scale[i]*national_hat[w], ranked at a 10% budget")
    print("(both rows scored on identical facility-weeks against an identical truth set)")
    print(f"\n{'test':<6}{'h':<3}{'clim window':<16}{'model':<14}{'recall':>9}{'precision':>11}"
          f"{'delta recall':>14}")
    beats = {}
    for test_year in AC2_BASELINE:
        for h in HORIZONS:
            for label, clim_from in (("post-COVID", BASELINE_TRAIN_FROM), ("full record", None)):
                r = stage2_alerts(panel, test_year, h, clim_from=clim_from)
                delta = r["stage 2"]["recall"] - r["climatology"]["recall"]
                for name in ("climatology", "stage 2"):
                    d = f"{delta:+.3f}" if name == "stage 2" else ""
                    print(f"{test_year:<6}{h:<3}{label:<16}{name:<14}"
                          f"{r[name]['recall']:>9.3f}{r[name]['precision']:>11.3f}{d:>14}")
                if h == 1 and clim_from == BASELINE_TRAIN_FROM:
                    beats[test_year] = delta

    print("\nORACLE control -- the realised national anomaly instead of the forecast (h=1,")
    print("post-COVID window). Not deployable: it says what the allocation is worth when")
    print("Stage 1 is right, which is how far Stage 3 could go by forecasting better.")
    for test_year in AC2_BASELINE:
        r = stage2_alerts(panel, test_year, 1, oracle=True)
        delta = r["stage 2"]["recall"] - r["climatology"]["recall"]
        print(f"{test_year:<6}{1:<3}{'post-COVID':<16}{'stage 2 ORACLE':<14}"
              f"{r['stage 2']['recall']:>9.3f}{r['stage 2']['precision']:>11.3f}{delta:>+14.3f}")

    print("\n\nStage 3 -- HistGradientBoosting on P(surge), ranked at a 10% budget  [AC2]")
    print("(all three models scored on identical rows; climatology is the criterion)")
    print(f"\n{'test':<6}{'h':<3}{'model':<14}{'recall':>9}{'precision':>11}{'d recall':>11}"
          f"{'d prec':>10}")
    ac2 = {}
    for test_year in AC2_BASELINE:
        for h in HORIZONS:
            r = stage3_alerts(panel, test_year, h)
            base = r["climatology"]
            for name in ("climatology", "stage 2", "stage 3"):
                dr = f"{r[name]['recall'] - base['recall']:+.3f}" if name != "climatology" else ""
                dp = f"{r[name]['precision'] - base['precision']:+.3f}" if name != "climatology" else ""
                print(f"{test_year:<6}{h:<3}{name:<14}{r[name]['recall']:>9.3f}"
                      f"{r[name]['precision']:>11.3f}{dr:>11}{dp:>10}")
            if h == 1:
                ac2[test_year] = r
            print(f"{'':<6}{'':<3}{'':<14}({r['n_train']:,} train rows, {r['n_test']:,} test)")

    print("\n\nAblation -- does the national wave earn its place in the alert list?  [h=1]")
    national = ["er", "er_hat", "stage2_z"]
    own = ["z", "z_l1", "z_l2", "z_d4"]
    sets = {"full (Stages 1+2+3)": STAGE3_FEATURES,
            "drop national": [c for c in STAGE3_FEATURES if c not in national],
            "own history + calendar": own + ["clim_z", "week"],
            "drop own history": [c for c in STAGE3_FEATURES if c not in own],
            # `03d`'s best composition, scored here so its 0.321 / 0.428 is commensurable
            "own+national+rings (03d)": own + national + RING_FEATURES + ["clim_z", "week"],
            "full + rings": STAGE3_FEATURES + RING_FEATURES}
    print(f"\n{'test':<6}{'features':<26}{'n':>3}{'recall':>9}{'precision':>11}")
    for test_year in AC2_BASELINE:
        for label, cols in sets.items():
            r = stage3_alerts(panel, test_year, 1, features=cols)["stage 3"]
            print(f"{test_year:<6}{label:<26}{len(cols):>3}{r['recall']:>9.3f}"
                  f"{r['precision']:>11.3f}")

    print("\n\nProspective budget -- the alert cut fixed on the season BEFORE the test year")
    print("(the within-year rank needs the whole season at once; deployment judges week 30 at 29)")
    print("A prospective cut does not spend exactly 10%, so read `lift`, not `recall`, across")
    print("rules; `silent` counts facilities that got no alert all season.")
    print(f"\n{'test':<6}{'h':<3}{'model':<14}{'budget':<15}{'recall':>9}{'precision':>11}"
          f"{'lift':>7}{'alert%':>9}{'silent':>8}")
    prosp = {}
    for test_year in AC2_BASELINE:
        for h in HORIZONS:
            r = prospective_alerts(panel, test_year, h)
            for name in ("climatology", "stage 3"):
                for rule in ("rank", "per facility", "national"):
                    s = r[name][rule]
                    print(f"{test_year:<6}{h:<3}{name:<14}{rule:<15}{s['recall']:>9.3f}"
                          f"{s['precision']:>11.3f}{s['lift']:>7.2f}{s['share'] * 100:>8.1f}%"
                          f"{s['silent']:>8}")
            if h == 1:
                prosp[test_year] = r

    print("\n\nProduct scope -- the same model scored on the population that can act on the alert")
    print("An ambulatory SAPU/SAR has 1-2 physicians per shift and no spare boxes: an alert there")
    print("has no lever. Averaging a metric over 446 such facilities was measuring the wrong")
    print("population. Prospective national cut, both models on identical rows.")
    scopes = {"full panel": None,
              "hospital ER (UEH)": hospital_er_facilities(panel),
              "high complexity": high_complexity_facilities(panel)}
    print(f"\n{'scope':<19}{'fac':>5}{'test':>6}{'h':>3}{'model':<13}{'recall':>9}{'prec':>8}"
          f"{'lift':>7}{'alert%':>8}{'silent':>8}")
    scoped = {}
    for label, fac in scopes.items():
        p = scope_panel(panel, fac)
        for test_year in AC2_BASELINE:
            for h in HORIZONS:
                r = prospective_alerts(p, test_year, h)
                for name in ("climatology", "stage 3"):
                    s = r[name]["national"]
                    print(f"{label:<19}{p['EstablecimientoCodigo'].nunique():>5}{test_year:>6}"
                          f"{h:>3} {name:<12}{s['recall']:>9.3f}{s['precision']:>8.3f}"
                          f"{s['lift']:>7.2f}{s['share'] * 100:>7.1f}%{s['silent']:>8}")
                if h == 1:
                    scoped[(label, test_year)] = r

    print("\n\nTwo-regime budget cut -- MEASURED AND NOT SHIPPED")
    print(f"The winter reinforcement budget only exists inside the declared campaign, so a wider")
    print(f"alert set is only actionable in weeks {CAMPAIGN_WEEKS.start}-{CAMPAIGN_WEEKS.stop - 1}."
          " Spending more there was the obvious")
    print("implementation. It fails: the campaign window is 14 weeks wide and holds only 23-28% of")
    print("surges -- barely more than its 27% share of rows -- so the extra budget lands on the")
    print("campaign's own quiet weeks. Worst in 2024, the wave year, which is the year that matters.")
    ueh = scope_panel(panel, hospital_er_facilities(panel))
    print(f"\n{'test':<6}{'h':<3}{'rule':<20}{'recall':>9}{'prec':>8}{'lift':>7}{'alert%':>8}")
    for test_year in AC2_BASELINE:
        for h in HORIZONS:
            r = prospective_alerts(ueh, test_year, h)["stage 3"]
            for rule in ("national", "two regime"):
                s = r[rule]
                tag = "national (SHIPPED)" if rule == "national" else "two regime @0.20"
                print(f"{test_year:<6}{h:<3}{tag:<20}{s['recall']:>9.3f}{s['precision']:>8.3f}"
                      f"{s['lift']:>7.2f}{s['share'] * 100:>7.1f}%")

    print("\n\nOnset vs continuation -- THE PRIMARY METRIC SINCE 2026-07-29")
    print("Every `recall` above is 52-64% surge CONTINUATION, and a shift coordinator sees an")
    print("ongoing surge from the waiting room. So the trivial rule -- alert iff already above")
    print("p90 -- beats what ships on recall, precision and lift in 2025 and in the sealed 2026.")
    print("That is a fact about the metric. Split the truth set and the picture inverts: at")
    print("MATCHED spend the shipped model takes roughly 2x the calendar's NEW surges and ~4x")
    print("persistence's, while persistence scores 0.000 at h=1 because it cannot flag a surge")
    print("that has not begun. Onsets are 36% (2024), 44% (2025), 48% (2026) of all surge weeks.")
    print("Hospital-ER scope. Every rule gets the shipped rule's own alert count -- rule 5.")
    print(f"\n{'test':<6}{'h':<3}{'rule':<20}{'onset':>8}{'contin':>8}{'all':>8}{'prec':>8}"
          f"{'N':>7}")
    onset_seasons = (2024, 2025, 2026)
    onset_cells = {}
    for test_year in onset_seasons:
        for h in HORIZONS:
            cal = stage3_predict(ueh, test_year - 1, h)[1]
            _, test = stage3_predict(ueh, test_year, h)
            n = int((test["prob"] >= cal["prob"].quantile(1 - ALERT_SHARE)).sum())
            # Persistence is a boolean, so a top-N ranking has to break its ties. Broken by the
            # model's own score, which is the CHARITABLE choice: when n exceeds the number of
            # facilities already in surge it hands persistence the model's next-best rows, and
            # that borrowed tail is where its onset recall (0.000 -> 0.053) comes from. A baseline
            # you intend to beat should be given every advantage.
            r = matched_spend(test, {"climatology": test["clim_z"],
                                     "stage 3 (SHIPPED)": test["prob"],
                                     "persistence": test["surge_now"].astype(float)
                                     + 1e-6 * test["prob"]}, n)
            onset_cells[(test_year, h)] = r
            for name, s in r.items():
                print(f"{test_year:<6}{h:<3}{name:<20}{s['onset_recall']:>8.3f}"
                      f"{s['contin_recall']:>8.3f}{s['recall']:>8.3f}{s['precision']:>8.3f}"
                      f"{n:>7,}")
            first = next(iter(r.values()))
            print(f"{'':<6}{'':<3}{'':<20}({first['onsets']:,} onsets of {first['surges']:,} "
                  f"surges = {first['onsets'] / max(first['surges'], 1):.0%}, "
                  f"{len(test):,} rows)")

    # Regression guard on the finding itself. Asserted at h=1 only, where the margin is the width
    # of persistence's structural zero (0.109-0.206 against 0.000-0.053) and cannot be flipped by
    # the run-to-run jitter documented in docs/ §9.3. The h=2 2025 cell is 0.217 vs 0.203 -- real,
    # but too narrow to assert on a non-reproducible fit.
    for test_year in onset_seasons:
        cell = onset_cells[(test_year, 1)]
        got, triv = cell["stage 3 (SHIPPED)"]["onset_recall"], cell["persistence"]["onset_recall"]
        assert got > triv, (f"the shipped model no longer beats persistence on NEW surges at "
                            f"h=1 in {test_year}: {got:.3f} vs {triv:.3f}. The product's whole "
                            f"claim is onset recall -- do not paper over this with aggregate lift.")

    def cells_won(against):
        return sum(r["stage 3 (SHIPPED)"]["onset_recall"] > r[against]["onset_recall"]
                   for r in onset_cells.values())

    print(f"\nOK  shipped model beats PERSISTENCE on new surges at h=1 in all "
          f"{len(onset_seasons)} seasons (asserted)")
    for against in ("climatology", "persistence"):
        won = cells_won(against)
        print(f"{'OK' if won >= 4 else '--'}  and beats {against:<12} on onset recall in "
              f"{won} of {len(onset_cells)} season x horizon cells")

    print("\n\nCalibration -- WHY THE SERVED COLUMN IS `score` AND NOT `surge_probability`")
    print("Isotonic fitted on the prior season, measured here and rejected: it makes the gap")
    print("worse, because the surge base rate moves 7.7% -> 13.3% between seasons and that is")
    print("the very thing being forecast. It also creates ties that move the alert set.")
    for test_year in AC2_BASELINE:
        cal = stage3_predict(panel, test_year - 1, 1)[1]
        _, test = stage3_predict(panel, test_year, 1)
        iso = fit_calibrator(cal)
        raw = test["prob"].to_numpy()
        cooked = iso.predict(raw)
        before, after = reliability(raw, test["surge"]), reliability(cooked, test["surge"])
        raw_cut = cal["prob"].quantile(1 - ALERT_SHARE)
        moved = int(((raw >= raw_cut) != (cooked >= float(iso.predict([raw_cut])[0]))).sum())
        print(f"\n  {test_year}   mean |gap| {before['gap'].abs().mean():.3f} -> "
              f"{after['gap'].abs().mean():.3f}    top decile pred/obs "
              f"{before['predicted'].iloc[-1]:.3f}/{before['observed'].iloc[-1]:.3f} -> "
              f"{after['predicted'].iloc[-1]:.3f}/{after['observed'].iloc[-1]:.3f}"
              f"    alert set moves {moved} of {len(test):,} rows")
        print(after.round(3).to_string())

    print("\n\nAC7 -- the alert list as a file")
    alert_list, path = write_alert_list(panel, 2025)
    print(f"{len(alert_list):,} rows -> {path.relative_to(ROOT).as_posix()}")
    print(alert_list.head(4).to_string(index=False))

    print("\nOK  no regression against the measured leak-free baseline")
    print("OK  AC2 baseline stable -- Stage 3 must beat recall "
          + ", ".join(f"{v['recall']:.3f} ({y})" for y, v in AC2_BASELINE.items()))
    ok = all(v > 0 for v in beats.values())
    print(f"{'OK' if ok else '--'}  Stage 2 {'beats' if ok else 'does NOT beat'} climatology at "
          f"h=1 in both years: " + ", ".join(f"{v:+.3f} ({y})" for y, v in beats.items()))

    passed = all(r["stage 3"]["recall"] > r["climatology"]["recall"]
                 and r["stage 3"]["precision"] >= r["climatology"]["precision"]
                 for r in ac2.values())
    print(f"{'OK' if passed else '--'}  AC2 {'MET' if passed else 'NOT met'} -- Stage 3 at h=1: "
          + ", ".join(f"{r['stage 3']['recall']:.3f} vs {r['climatology']['recall']:.3f} ({y})"
                      for y, r in ac2.items()))

    # Lift, not recall: a prospective cut lets the spend drift, so recall is not comparable
    # between rules. Both models are calibrated the same way on the same season.
    held = all(r["stage 3"][rule]["lift"] > r["climatology"][rule]["lift"]
               for r in prosp.values() for rule in ("per facility", "national"))
    print(f"{'OK' if held else '--'}  AC2 {'survives' if held else 'does NOT survive'} a "
          "prospective cut at h=1, on lift: "
          + ", ".join(f"{r['stage 3']['per facility']['lift']:.2f} vs "
                      f"{r['climatology']['per facility']['lift']:.2f} ({y})"
                      for y, r in prosp.items()))

    # AC2 on the product's own population, which is the version that counts since 2026-07-29.
    # Asserted separately from the full-panel guard above: that one is a regression check on a
    # baseline computed over 623 facilities, this one is the acceptance criterion.
    on_scope = [(label, y, r) for (label, y), r in scoped.items() if label != "full panel"]
    scope_ok = all(r["stage 3"]["national"]["recall"] > r["climatology"]["national"]["recall"]
                   and r["stage 3"]["national"]["precision"]
                   >= r["climatology"]["national"]["precision"]
                   for _, _, r in on_scope)
    print(f"{'OK' if scope_ok else '--'}  AC2 {'MET' if scope_ok else 'NOT met'} on the hospital "
          "scope at h=1, national cut: "
          + ", ".join(f"{r['stage 3']['national']['lift']:.2f} vs "
                      f"{r['climatology']['national']['lift']:.2f} ({label[:3]} {y})"
                      for label, y, r in on_scope))


if __name__ == "__main__":
    demo()
