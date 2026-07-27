"""The surge-alert model: rank each facility's weeks by the risk of exceeding its own p90.

**What ships is `DEPLOYED_FEATURES` -- six columns and one classifier.** The three-stage design
this module was written against (national wave -> factor allocation -> classifier) is all here and
all measured, but the ablation in `demo()` found Stages 1 and 2 contribute under 0.01 recall to the
alert list: the national anomaly is by construction the mean of the very `z` values the classifier
already holds per facility. They are kept for reporting and as the record of that measurement.

Read `demo()` output top to bottom -- it is the argument for every choice below.

Four things cost real work to learn and must not be undone:

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

Spec: context/specs/surge-alert-model.md · Decisions: context/decisions/log.md, 2026-07-27.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
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

# Stage 3 must beat this. Measured below, post-COVID window (see BASELINE_TRAIN_FROM), by the same
# `score_alerts` that will score Stage 3 -- a benchmark computed by other code is not a benchmark.
BASELINE_TRAIN_FROM = 2022
AC2_BASELINE = {2025: {"recall": 0.232, "precision": 0.184},
                2024: {"recall": 0.252, "precision": 0.351}}


def alert_flags(test, pred):
    """The top `ALERT_SHARE` of each facility's own weeks, ranked by `pred`."""
    facility = test["EstablecimientoCodigo"]
    rank = pd.Series(np.asarray(pred), index=test.index).groupby(facility).rank(
        ascending=False, method="first")
    return rank <= facility.map(facility.value_counts()) * ALERT_SHARE


def score_alerts(test, pred):
    """Recall/precision at a fixed alert budget: each facility alerts its own top 10% of weeks.

    `pred` ranks the facility's weeks; only the ordering matters, not the units. `test` supplies
    the boolean `surge` column. This is the metric the project is judged on -- an R2 gain that
    does not re-order this list is not a result.
    """
    alert, truth = alert_flags(test, pred), test["surge"]

    tp = int((alert & truth).sum())
    return {
        "recall": tp / max(int(truth.sum()), 1),
        "precision": tp / max(int(alert.sum()), 1),
        "alerts": int(alert.sum()),
        "surges": int(truth.sum()),
    }


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
              "clim_fut": C.shift(-h), "lvl_fut": L.shift(-h), **ring_means(Z, coords)}
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


ALERT_LIST = ROOT / "data" / "processed" / "alert_list.parquet"


def write_alert_list(panel, test_year, horizons=HORIZONS, path=ALERT_LIST):
    """AC7: the serving interface. One row per (facility, target week, horizon).

    Nothing downstream should need to import this module -- it reads this file.
    """
    out = []
    for h in horizons:
        _, test = stage3_predict(panel, test_year, h)
        out.append(pd.DataFrame({
            "facility": test["EstablecimientoCodigo"].to_numpy(),
            "year": test_year,
            "week": test["week"].to_numpy(),
            "horizon": h,
            "surge_probability": test["prob"].to_numpy(),
            "alert": alert_flags(test, test["prob"]).to_numpy(),
            "observed_surge": test["surge"].to_numpy(),   # blank in live use; the target week
        }))                                               # has not happened yet

    df = pd.concat(out, ignore_index=True).sort_values(
        ["horizon", "week", "surge_probability"], ascending=[True, True, False])
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


if __name__ == "__main__":
    demo()
