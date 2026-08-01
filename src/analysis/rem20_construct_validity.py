"""Does a p90 respiratory week coincide with measurable inpatient strain?

VitalFlow forecasts weeks above a facility's own 90th percentile of respiratory *attentions*. That
is a demand percentile. The product is sold as an early warning of *strain*. This module tests
whether the two coincide, using the only capacity measure the project holds: REM20 monthly bed
occupancy.

Pre-registered in `context/specs/rem20-construct-validity.md` before this file existed. Read it
before changing anything here -- the areas, the windows, the statistic and the decision rule were
all fixed in advance, and the negative controls are what make a positive result interpretable.

Three constraints, all known before running (decisions/log.md, 2026-07-29):

* **Hospital ERs only.** 179 of 180 UEH join; 0 of 446 ambulatory facilities do, and those carry
  73.7% of respiratory volume. No result here speaks for them in either direction.
* **Monthly against weekly.** The surge label must be coarsened to facility-month. Expect low power;
  a null is weak evidence of no association, not evidence of none.
* **Winter confounds everything.** Demand and occupancy both peak in the southern winter, so the
  primary outcome is the occupancy *anomaly* against the facility's own month-of-year norm -- the
  same argument as `build_features.deseasonalize`.
"""

from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))

from src.features.build_features import load_weekly_target  # noqa: E402
from src.models.train_model import SURGE_QUANTILE, Y, hospital_er_facilities  # noqa: E402

REM20_CSV = (
    ROOT / "data" / "raw" / "Atenciones de Urgencia"
    / "Indicadores del proceso de hospitalización de los establecimientos públicos de Salud"
    / "indicadores_rem20_20260625.csv"
)

# Chosen before any result was seen -- spec "Functional areas". 403/404 Médico-Quirúrgico are
# deliberately in neither set: they absorb medical overflow, so they are neither signal nor control.
PRIMARY_AREAS = [401, 402, 405, 406, 407, 408, 411, 412]   # adult + paediatric medicine and ICU
CONTROL_AREAS = [416, 418]                                  # obstetrics, adult short-stay psychiatry

PRIMARY_WINDOW = range(2022, 2027)   # the era the product ships in
REPLICATION_WINDOW = range(2015, 2020)   # pre-COVID, its own era-relative p90
MIN_MONTHS_PER_ARM = 3               # a facility needs >=3 surge and >=3 non-surge months to enter


def load_rem20(con=None):
    """Facility × area × month bed statistics. Percentages are never read -- they are recomputed.

    `INDICE_OCUPACIONAL` in the file equals 100 * DIAS_CAMAS_OCUPADAS / DIAS_CAMAS_DISPONIBLES
    (verified in demo()), so summing the two day-counts across areas gives the exact pooled index.
    Averaging the published percentages instead would weight a 6-bed ICU like a 60-bed ward.
    """
    con = con or duckdb.connect()
    return con.execute(f"""
        SELECT PERIODO AS anio, MES AS mes,
               -- The target's EstablecimientoCodigo is a string; REM20's parses as int64 and the
               -- merge would raise. 179 of 180 UEH match on the bare code, no homologation needed.
               CAST(CODIGO_ESTABLECIMIENTO AS VARCHAR) AS cod, COD_AREA_FUNCIONAL AS area,
               DIAS_CAMAS_OCUPADAS AS ocu, DIAS_CAMAS_DISPONIBLES AS disp,
               DIAS_ESTADA AS estada, NUMERO_EGRESOS AS egresos,
               INDICE_OCUPACIONAL AS occ_published
        FROM read_csv_auto('{REM20_CSV.as_posix()}', delim=';', header=true)
    """).df()


def facility_month_occupancy(rem, areas, years):
    """Pool the chosen areas into one occupancy index per facility-month."""
    sub = rem[rem["area"].isin(areas) & rem["anio"].isin(years)]
    fm = sub.groupby(["cod", "anio", "mes"], as_index=False)[["ocu", "disp", "estada", "egresos"]].sum()
    fm = fm[fm["disp"] > 0].copy()
    fm["occ"] = 100 * fm["ocu"] / fm["disp"]
    fm["estada_prom"] = fm["estada"] / fm["egresos"].replace(0, np.nan)
    return fm


def iso_month(anio, semana):
    """The month a DEIS epidemiological week belongs to: the month of its Thursday.

    The weekly file carries no dates, only (Anio, SemanaEstadistica), so the ISO Thursday rule is
    the reconstruction available. `build_features` records that DEIS weeks may sit a few days off
    ISO; the offset is constant, so it can move a week across a month boundary but cannot bias the
    contrast in a direction.
    """
    return np.array([date.fromisocalendar(int(a), int(w), 4).month
                     for a, w in zip(anio, semana)])


def surge_facility_months(years, con=None):
    """Facility-month surge counts over hospital ERs, labelled by the facility's own era p90."""
    target = load_weekly_target(min(years), max(years), con=con)
    target = target[target["Anio"].isin(years)]
    target = target[target["EstablecimientoCodigo"].isin(hospital_er_facilities(target))].copy()

    thr = target.groupby("EstablecimientoCodigo")[Y].quantile(SURGE_QUANTILE)
    target["surge"] = target[Y] > target["EstablecimientoCodigo"].map(thr)
    target["mes"] = iso_month(target["Anio"], target["SemanaEstadistica"])

    fm = (target.groupby(["EstablecimientoCodigo", "Anio", "mes"], as_index=False)
          .agg(n_surge_weeks=("surge", "sum"), n_weeks=("surge", "size")))
    return fm.rename(columns={"EstablecimientoCodigo": "cod", "Anio": "anio"})


def deseasonalize(fm, col="occ"):
    """Occupancy anomaly in facility SD units: minus the facility's own month-of-year norm.

    Divided by the SD of the *raw* series, not of the anomaly -- deliberately conservative, and it
    is what the pre-registration says.
    """
    norm = fm.groupby(["cod", "mes"])[col].transform("mean")
    sd = fm.groupby("cod")[col].transform("std")
    return (fm[col] - norm) / sd.replace(0, np.nan)


def facility_contrast(joined, value_col):
    """Per facility: mean(value | surge month) - mean(value | non-surge month).

    The facility is the unit of analysis. Pooling facility-months instead would let a handful of
    large facilities with many months carry the estimate.
    """
    d = joined.dropna(subset=[value_col])
    g = d.groupby(["cod", d["n_surge_weeks"] > 0])[value_col].agg(["mean", "size"]).unstack()
    ok = (g[("size", False)] >= MIN_MONTHS_PER_ARM) & (g[("size", True)] >= MIN_MONTHS_PER_ARM)
    return (g.loc[ok, ("mean", True)] - g.loc[ok, ("mean", False)]).rename("d")


def bootstrap_median(d, n=10_000, seed=0):
    """95% CI on the median contrast, resampling facilities. No distributional assumption."""
    if len(d) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    x = np.asarray(d, float)
    draws = np.median(x[rng.integers(0, len(x), size=(n, len(x)))], axis=1)
    return tuple(np.percentile(draws, [2.5, 97.5]))


def run(years, areas, rem=None, surge=None, label="", con=None):
    """One arm of the test: join, contrast, bootstrap. Returns a dict of everything reported."""
    rem = load_rem20(con) if rem is None else rem
    surge = surge_facility_months(years, con=con) if surge is None else surge

    fm = facility_month_occupancy(rem, areas, years)
    fm["occ_anom"] = deseasonalize(fm, "occ")
    # The same anomaly without the SD division: percentage points of occupancy, which is the only
    # unit anyone in a hospital can act on. "+0.09 SD" is not a readable effect size.
    fm["occ_anom_pp"] = fm["occ"] - fm.groupby(["cod", "mes"])["occ"].transform("mean")
    fm["estada_anom"] = deseasonalize(fm, "estada_prom")
    joined = fm.merge(surge, on=["cod", "anio", "mes"], how="inner")

    out = {
        "label": label,
        "facilities_rem20": fm["cod"].nunique(),
        "facilities_joined": joined["cod"].nunique(),
        "facility_months": len(joined),
    }
    for name, col in [("anom", "occ_anom"), ("anom_pp", "occ_anom_pp"),
                      ("raw", "occ"), ("estada", "estada_anom")]:
        d = facility_contrast(joined, col)
        lo, hi = bootstrap_median(d)
        out[name] = {"n": len(d), "median": d.median(), "share_pos": (d > 0).mean(),
                     "ci": (lo, hi)}

    dose = joined.assign(bucket=np.minimum(joined["n_surge_weeks"], 3))
    out["dose"] = dose.groupby("bucket").agg(sd=("occ_anom", "mean"),
                                             pp=("occ_anom_pp", "mean"),
                                             n=("occ_anom", "size"))
    return out


def _fmt(r):
    return (f"median {r['median']:+.3f}  CI [{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]  "
            f"pos {r['share_pos']:.0%}  n={r['n']}")


def report(con=None):
    """The pre-registered test, both windows, primary areas and negative controls."""
    con = con or duckdb.connect()
    rem = load_rem20(con)

    for years, wname in [(PRIMARY_WINDOW, "PRIMARY 2022-2026"),
                         (REPLICATION_WINDOW, "REPLICATION 2015-2019")]:
        surge = surge_facility_months(years, con=con)
        print(f"\n=== {wname} " + "=" * (58 - len(wname)))
        arms = {}
        for areas, aname in [(PRIMARY_AREAS, "primary areas"), (CONTROL_AREAS, "NEGATIVE controls")]:
            r = run(years, areas, rem=rem, surge=surge, label=aname, con=con)
            arms[aname] = r
            # AC-R1: the join is reported before any outcome.
            print(f"\n{aname}: {r['facilities_rem20']} facilities in REM20 -> "
                  f"{r['facilities_joined']} joined, {r['facility_months']:,} facility-months")
            print(f"  occupancy anomaly (PRIMARY)  {_fmt(r['anom'])}")
            print(f"  same, percentage points      {_fmt(r['anom_pp'])}")
            print(f"  occupancy raw, no season ctl {_fmt(r['raw'])}")
            print(f"  mean stay anomaly (2ndary)   {_fmt(r['estada'])}")
        p, c = arms["primary areas"]["anom"], arms["NEGATIVE controls"]["anom"]
        print(f"\n  dose-response, primary areas (surge weeks in month -> mean anomaly):")
        print("   " + arms["primary areas"]["dose"].to_string().replace("\n", "\n   "))
        print(f"\n  PASS requires median>0 with CI excluding 0 AND primary > controls: "
              f"{p['median']:+.3f} vs {c['median']:+.3f}  -> "
              f"{'PASS' if p['ci'][0] > 0 and p['median'] > c['median'] else 'NOT PASSED'}")


def demo():
    """Self-check on the two reconstructions this module depends on."""
    # The published percentage must be reproducible from the day counts, or pooling areas is invalid.
    rem = load_rem20()
    s = rem[(rem["disp"] > 0) & rem["occ_published"].notna()].head(5000)
    resid = (100 * s["ocu"] / s["disp"] - s["occ_published"]).abs()
    assert resid.max() < 0.05, f"INDICE_OCUPACIONAL is not ocu/disp (max resid {resid.max():.3f})"

    # Week -> month by the ISO Thursday. Both sides of a month boundary, and a year boundary.
    assert list(iso_month([2024, 2024, 2025], [44, 45, 1])) == [10, 11, 1]

    # The contrast must find nothing when there is nothing, and find what is planted.
    rng = np.random.default_rng(0)
    n = 600
    fake = pd.DataFrame({
        "cod": np.repeat(np.arange(30), 20),
        "n_surge_weeks": rng.integers(0, 2, n),
        "noise": rng.normal(size=n),
    })
    d0 = facility_contrast(fake, "noise")
    assert abs(d0.median()) < 0.3, f"contrast invents an effect on noise: {d0.median():+.3f}"
    fake["planted"] = fake["noise"] + (fake["n_surge_weeks"] > 0)
    d1 = facility_contrast(fake, "planted")
    assert 0.7 < d1.median() < 1.3, f"contrast misses a planted +1 SD effect: {d1.median():+.3f}"
    lo, hi = bootstrap_median(d1)
    assert lo > 0, "bootstrap CI should exclude 0 on a planted effect"

    print(f"OK  REM20 {len(rem):,} rows · occupancy reconstruction max resid {resid.max():.4f} · "
          f"contrast: noise {d0.median():+.3f}, planted {d1.median():+.3f}")


if __name__ == "__main__":
    demo()
    report()
