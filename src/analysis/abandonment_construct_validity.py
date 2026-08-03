"""Does a p90 respiratory week coincide with strain at the AMBULATORY facilities?

`rem20_construct_validity.py` answered this for hospital ERs and refused, explicitly, to say
anything about the 446 ambulatory facilities that carry 73.7% of respiratory volume -- they hold no
inpatient beds and appear in no bed-occupancy report. `PRODUCT.md` recorded that as "formally
untestable, not merely untested".

That was wrong, and this module is the consequence. The daily SADU file carries `IdCausa = 34`
("TOTAL DEMANDA") alongside `IdCausa = 1` ("TOTAL ATENCIONES"), and the official REM manual defines
demanda as everyone who generated a DAU *including those who abandoned before discharge*
(Manual Series REM 2025-2026 Serie A, SS A.1 p.203 and A.2 p.205; validation rule R.4 requires
demanda >= atenciones). So:

    demanda - atenciones  =  people who left before being discharged

That is a demand-side strain measure, not a capacity denominator -- and unlike beds it exists for
SAPU, SAR and SUR.

Pre-registered in `context/specs/abandonment-construct-validity.md` before this file existed. Read
it before changing anything: the strata, the windows, the statistic, the two placebo controls and
the decision rule were all fixed in advance, and the spec's "Disclosure" section records exactly
what had been seen when the predictions were written.

Three biases known before running, all declared in the spec:

* **`demanda` is all-cause, not respiratory.** A respiratory wave is a fraction of total volume, so
  the signal is diluted toward the null. A positive result is conservative; a null is weak evidence.
* **The daily file ends 2024-12-31 and covers 359 facilities, not 632.** This is not the window the
  model ships in, and it cannot be made so -- no other file carries `IdCausa = 34`.
* **Reporting quality is unmeasured.** A facility reporting a constant zero gap is not a facility
  without abandonments, so the always-zero count is a reported result (AC-A2), not a silent drop.
"""

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))

from src.analysis.rem20_construct_validity import bootstrap_median  # noqa: E402
from src.features.build_features import load_weekly_target  # noqa: E402
from src.models.train_model import SURGE_QUANTILE, Y  # noqa: E402

DAILY_DIR = ROOT / "data" / "processed" / "urgencias_parquet"
REGISTRY = (
    ROOT / "data" / "raw" / "Atenciones de Urgencia" / "Establecimientos de Salud"
    / "establecimientos_20260714.csv"
)

CAUSA_ATENCIONES = 1    # "SECCIÓN 1. TOTAL ATENCIONES DE URGENCIA"
CAUSA_DEMANDA = 34      # "TOTAL DEMANDA" -- attentions + abandonments, per the REM manual

PRIMARY_WINDOW = range(2022, 2025)      # post-COVID; the daily file ends 2024-12-31
REPLICATION_WINDOW = range(2017, 2020)  # pre-COVID, its own era-relative p90
MIN_WEEKS_PER_ARM = 5                   # stricter than REM20's 3 -- weekly gives more rows

AMBULATORY = ["SAPU", "SAR", "SUR"]     # the primary stratum: what REM20 is structurally silent on


def load_crosswalk(con=None):
    """Daily `IdEstablecimiento` ("01-100") -> weekly `EstablecimientoCodigo` ("101100").

    The two files use different code systems and there is no arithmetic transform between them:
    stripping the first character matches only 203 of 359. The registry's
    `EstablecimientoCodigoAntiguo` column is the official crosswalk and matches all 359.
    """
    con = con or duckdb.connect()
    return con.execute(f"""
        SELECT DISTINCT trim(CAST(EstablecimientoCodigoAntiguo AS VARCHAR)) AS id_daily,
                        trim(CAST(EstablecimientoCodigo AS VARCHAR))        AS cod
        FROM read_csv_auto('{REGISTRY.as_posix()}', ignore_errors=true)
        WHERE EstablecimientoCodigoAntiguo IS NOT NULL
    """).df()


def load_facility_week_demand(years, con=None):
    """Facility × epidemiological week: attentions, demand, and the abandonment rate between them.

    `Total` is summed over whole rows of one cause section, so this never touches the respiratory
    breakdown and never re-writes the target query (CLAUDE.md).
    """
    con = con or duckdb.connect()
    files = [DAILY_DIR / f"AtencionesUrgencia{y}.parquet" for y in years]
    files = [f for f in files if f.exists()]
    assert files, f"no daily parquet for {list(years)} in {DAILY_DIR}"
    globs = ", ".join(f"'{f.as_posix()}'" for f in files)

    fw = con.execute(f"""
        SELECT trim(IdEstablecimiento) AS id_daily,
               any_value(GLOSATIPOESTABLECIMIENTO) AS tipo,
               CAST(year(strptime(fecha, '%d/%m/%Y')) AS INTEGER) AS anio,
               CAST(semana AS INTEGER) AS semana,
               SUM(CASE WHEN IdCausa = {CAUSA_ATENCIONES} THEN Total ELSE 0 END) AS atenciones,
               SUM(CASE WHEN IdCausa = {CAUSA_DEMANDA}    THEN Total ELSE 0 END) AS demanda
        FROM read_parquet([{globs}])
        WHERE IdCausa IN ({CAUSA_ATENCIONES}, {CAUSA_DEMANDA})
        GROUP BY ALL
        ORDER BY id_daily, anio, semana   -- rule 19: never leave row order to the engine
    """).df()

    fw = fw[fw["anio"].isin(list(years))]
    return fw.merge(load_crosswalk(con), on="id_daily", how="inner")


def abandonment_rate(fw):
    """(demanda - atenciones) / demanda, with the two data-quality classes counted, not hidden.

    R.4 of the REM manual requires demanda >= atenciones. Rows that violate it are reporting
    errors, not negative abandonment, so they are dropped -- and counted, because how many there
    are is itself evidence about whether this measure can be used at all.
    """
    fw = fw.copy()
    fw["r4_violation"] = fw["demanda"] < fw["atenciones"]
    ok = (fw["demanda"] > 0) & ~fw["r4_violation"]
    fw["aband"] = np.where(ok, (fw["demanda"] - fw["atenciones"]) / fw["demanda"], np.nan)
    return fw


def surge_facility_weeks(years, con=None):
    """One row per (facility, year, week) with the facility's own era-relative p90 surge label."""
    target = load_weekly_target(min(years), max(years), con=con)
    target = target[target["Anio"].isin(list(years))].copy()

    thr = target.groupby("EstablecimientoCodigo")[Y].quantile(SURGE_QUANTILE)
    target["surge"] = target[Y] > target["EstablecimientoCodigo"].map(thr)
    return (target[["EstablecimientoCodigo", "Anio", "SemanaEstadistica", "surge", Y]]
            .rename(columns={"EstablecimientoCodigo": "cod", "Anio": "anio",
                             "SemanaEstadistica": "semana", Y: "respiratorias"}))


def deseasonalize(fw, col="aband"):
    """Anomaly in facility SD units: minus the facility's own week-of-year norm.

    Same argument as REM20's month-of-year version and as `build_features.deseasonalize` -- both
    respiratory demand and abandonment peak in the southern winter, so an uncontrolled contrast
    mostly measures "winter resembles winter".
    """
    norm = fw.groupby(["cod", "semana"])[col].transform("mean")
    sd = fw.groupby("cod")[col].transform("std")
    return (fw[col] - norm) / sd.replace(0, np.nan)


def remove_national(fw, col):
    """Strip the cross-facility mean anomaly per (year, week).

    The week-of-year control removes *average* seasonality, not year-to-year severity: a bad season
    lifts surges and abandonment everywhere at once, which the contrast would read as association.
    The REM20 audit had to add this after publication and it cost ~40% of the effect. Here it is
    primary, per the pre-registration.
    """
    return fw[col] - fw.groupby(["anio", "semana"])[col].transform("mean")


def facility_contrast(joined, value_col, min_per_arm=MIN_WEEKS_PER_ARM):
    """Per facility: mean(value | surge week) - mean(value | non-surge week).

    The facility is the unit of analysis; pooling facility-weeks would let a few high-volume
    facilities with long series carry the estimate.
    """
    d = joined.dropna(subset=[value_col])
    g = d.groupby(["cod", d["surge"]])[value_col].agg(["mean", "size"]).unstack()
    if ("size", True) not in g or ("size", False) not in g:
        return pd.Series(dtype=float, name="d")
    ok = (g[("size", False)] >= min_per_arm) & (g[("size", True)] >= min_per_arm)
    return (g.loc[ok, ("mean", True)] - g.loc[ok, ("mean", False)]).rename("d")


def placebo_labels(joined, seed=0):
    """The two pre-registered negative controls, both placebos on the label.

    The informative confound here is "this facility is busy", which is the mechanism rather than a
    confound -- so the controls attack the label, not the outcome.
    """
    rng = np.random.default_rng(seed)
    out = joined.copy()
    # Permuted within facility: same number of surge weeks, wrong weeks.
    out["surge_perm"] = out.groupby("cod")["surge"].transform(
        lambda s: rng.permutation(s.to_numpy())
    )
    # Half a year out of phase. Under the week-of-year control the expected anomaly is 0 by
    # construction, so a non-zero result here means the deseasonalisation is not working.
    shifted = out[["cod", "anio", "semana", "surge"]].copy()
    shifted["semana"] = ((shifted["semana"] + 26 - 1) % 52) + 1
    shifted = shifted.rename(columns={"surge": "surge_shift"})
    return out.merge(shifted, on=["cod", "anio", "semana"], how="left")


def run(years, stratum, con=None, fw=None, surge=None, label=""):
    """One arm: build, control, contrast, bootstrap. Returns everything the report prints."""
    fw = abandonment_rate(load_facility_week_demand(years, con=con)) if fw is None else fw
    surge = surge_facility_weeks(years, con=con) if surge is None else surge

    sub = fw[fw["tipo"].isin(stratum)].copy()
    coverage = {
        "facilities_daily": sub["id_daily"].nunique(),
        "r4_violations": int(sub["r4_violation"].sum()),
        "facility_weeks": len(sub),
    }
    # AC-A2: a facility whose gap is always zero is a reporting artifact, not a clean facility.
    gap_sd = sub.groupby("cod")["aband"].std()
    always_zero = sorted(gap_sd[(gap_sd.isna()) | (gap_sd == 0)].index)
    coverage["always_zero"] = len(always_zero)
    sub = sub[~sub["cod"].isin(always_zero)]

    sub["anom"] = deseasonalize(sub, "aband")
    sub["anom_net"] = remove_national(sub, "anom")

    joined = sub.merge(surge, on=["cod", "anio", "semana"], how="inner")
    joined = placebo_labels(joined)
    coverage["facilities_joined"] = joined["cod"].nunique()

    out = {"label": label, **coverage}
    for name, col in [("primary", "anom_net"), ("no_national", "anom"), ("raw", "aband")]:
        d = facility_contrast(joined, col)
        lo, hi = bootstrap_median(d)
        out[name] = {"n": len(d), "median": d.median(), "share_pos": (d > 0).mean(), "ci": (lo, hi)}

    for name, lab in [("perm", "surge_perm"), ("shift", "surge_shift")]:
        placebo = joined.drop(columns="surge").rename(columns={lab: "surge"}).dropna(subset=["surge"])
        d = facility_contrast(placebo, "anom_net")
        lo, hi = bootstrap_median(d)
        out[name] = {"n": len(d), "median": d.median(), "share_pos": (d > 0).mean(), "ci": (lo, hi)}

    out["n_facilities_final"] = out["primary"]["n"]
    return out


def _fmt(r):
    return (f"median {r['median']:+.3f}  CI [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]  "
            f"pos {r['share_pos']:.0%}  n={r['n']}")


def report(con=None):
    """The pre-registered test: both windows, both strata, both placebos."""
    con = con or duckdb.connect()

    for years, wname in [(PRIMARY_WINDOW, "PRIMARY 2022-2024"),
                         (REPLICATION_WINDOW, "REPLICATION 2017-2019")]:
        fw = abandonment_rate(load_facility_week_demand(years, con=con))
        surge = surge_facility_weeks(years, con=con)
        print(f"\n=== {wname} " + "=" * (60 - len(wname)))

        arms = {}
        for stratum, sname in [(AMBULATORY, "AMBULATORY (primary)"), (["Hospital"], "hospital")]:
            r = run(years, stratum, fw=fw, surge=surge, label=sname, con=con)
            arms[sname] = r
            # AC-A1 / AC-A2: coverage and data quality before any outcome.
            print(f"\n{sname}: {r['facilities_daily']} in daily file -> "
                  f"{r['facilities_joined']} joined the target -> {r['n_facilities_final']} pass "
                  f">={MIN_WEEKS_PER_ARM}/arm")
            print(f"  {r['facility_weeks']:,} facility-weeks · "
                  f"{r['always_zero']} always-zero-gap facilities dropped · "
                  f"{r['r4_violations']:,} R.4 violations dropped")
            print(f"  abandonment anomaly, national removed (PRIMARY) {_fmt(r['primary'])}")
            print(f"  same, national component kept                   {_fmt(r['no_national'])}")
            print(f"  raw rate, no seasonal control                   {_fmt(r['raw'])}")
            print(f"  PLACEBO permuted label                          {_fmt(r['perm'])}")
            print(f"  PLACEBO shifted 26 weeks                        {_fmt(r['shift'])}")

        p = arms["AMBULATORY (primary)"]
        passed = (p["primary"]["ci"][0] > 0
                  and p["primary"]["median"] > p["perm"]["median"]
                  and p["primary"]["median"] > p["shift"]["median"])
        print(f"\n  PASS requires ambulatory median>0 with CI excluding 0 AND above both placebos:")
        print(f"    {p['primary']['median']:+.3f}  vs perm {p['perm']['median']:+.3f} / "
              f"shift {p['shift']['median']:+.3f}  ->  {'PASS' if passed else 'NOT PASSED'}")


def audit(years=PRIMARY_WINDOW, stratum=AMBULATORY, con=None):
    """Why is the pre-registered rate contrast NEGATIVE? NOT pre-registered -- run after the result.

    The primary outcome is a *rate*: (demanda - atenciones) / demanda. A surge week raises the
    denominator by definition -- that is what a surge is -- so the rate can fall while the number of
    people walking out rises. That is the single most obvious alternative reading of a negative
    result and it must be checked before the result is described as "no strain signal".

    Same shape as REM20's audit B (numerator vs denominator), and reported whatever it says. It does
    NOT replace the pre-registered outcome: switching to whichever statistic came out positive is
    exactly the outcome-switching this project's protocol exists to prevent.
    """
    con = con or duckdb.connect()
    fw = abandonment_rate(load_facility_week_demand(years, con=con))
    surge = surge_facility_weeks(years, con=con)

    sub = fw[fw["tipo"].isin(stratum)].copy()
    gap_sd = sub.groupby("cod")["aband"].std()
    sub = sub[~sub["cod"].isin(gap_sd[(gap_sd.isna()) | (gap_sd == 0)].index)]
    sub["abandonos"] = sub["demanda"] - sub["atenciones"]

    print(f"\n=== AUDIT: rate, or its two parts? ({'/'.join(stratum)}, {min(years)}-{max(years)}) "
          + "=" * 8)
    print("  NOT pre-registered. The rate contrast above is the result; this explains its sign.")
    for col, name in [("aband", "rate (demanda-atenciones)/demanda  [PRE-REG]"),
                      ("abandonos", "  numerator: people who walked out"),
                      ("demanda", "  denominator: total demand"),
                      ("atenciones", "  for reference: attentions")]:
        sub[f"{col}_anom"] = deseasonalize(sub, col)
        sub[f"{col}_net"] = remove_national(sub, f"{col}_anom")
        j = sub.merge(surge, on=["cod", "anio", "semana"], how="inner")
        d = facility_contrast(j, f"{col}_net")
        lo, hi = bootstrap_median(d)
        print(f"  {name:<46} median {d.median():+.3f}  CI [{lo:+.3f}, {hi:+.3f}]  "
              f"pos {(d > 0).mean():.0%}  n={len(d)}")


def demo():
    """AC-A7: the crosswalk, the week alignment, and that the contrast neither invents nor misses."""
    con = duckdb.connect()

    # The crosswalk is the whole test's foundation -- a wrong join silently analyses noise.
    xw = load_crosswalk(con)
    known = xw.set_index("id_daily")["cod"]
    assert known.get("01-100") == "101100", f"crosswalk broken: 01-100 -> {known.get('01-100')}"

    fw = load_facility_week_demand([2024], con=con)
    assert fw["cod"].nunique() > 300, f"only {fw['cod'].nunique()} facilities crossed the registry"

    # AC-A3: the two files must agree on what an epidemiological week is. If they do not, every
    # contrast below is comparing a facility's demand in week w to its surges in some other week.
    # The strongest available check is that respiratory attentions reconcile between the files.
    daily_resp = con.execute(f"""
        SELECT trim(IdEstablecimiento) AS id_daily, CAST(semana AS INTEGER) AS semana,
               SUM(Total) AS resp
        FROM read_parquet('{(DAILY_DIR / "AtencionesUrgencia2024.parquet").as_posix()}')
        WHERE IdCausa = 2 GROUP BY ALL
    """).df().merge(xw, on="id_daily")
    weekly = surge_facility_weeks([2024], con=con)
    m = daily_resp.merge(weekly[weekly["anio"] == 2024], on=["cod", "semana"], how="inner")
    assert len(m) > 10_000, f"only {len(m)} facility-weeks aligned between the two files"
    agree = np.isclose(m["resp"], m["respiratorias"], rtol=0.02, atol=2).mean()
    assert agree > 0.90, f"week conventions disagree: only {agree:.1%} of totals reconcile"

    # The contrast must find nothing when there is nothing, and find what is planted.
    rng = np.random.default_rng(0)
    n = 900
    fake = pd.DataFrame({
        "cod": np.repeat(np.arange(30), 30),
        "surge": rng.integers(0, 2, n).astype(bool),
        "noise": rng.normal(size=n),
    })
    d0 = facility_contrast(fake, "noise")
    assert abs(d0.median()) < 0.3, f"contrast invents an effect on noise: {d0.median():+.3f}"
    fake["planted"] = fake["noise"] + fake["surge"]
    d1 = facility_contrast(fake, "planted")
    assert 0.7 < d1.median() < 1.3, f"contrast misses a planted +1 SD effect: {d1.median():+.3f}"
    assert bootstrap_median(d1)[0] > 0, "bootstrap CI should exclude 0 on a planted effect"

    print(f"OK  crosswalk {len(xw):,} rows · {fw['cod'].nunique()} facilities joined · "
          f"week alignment {agree:.1%} of {len(m):,} facility-weeks · "
          f"contrast: noise {d0.median():+.3f}, planted {d1.median():+.3f}")


if __name__ == "__main__":
    demo()
    report()
