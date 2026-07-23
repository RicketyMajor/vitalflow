"""Weekly facility panel: respiratory ER demand joined to air-quality exposure.

Builds the analytical table used to test the project's central hypothesis — that air
pollution predicts respiratory emergency demand — and, later, to feed HDBSCAN and the TFT.

Design notes worth knowing before using this:

* **Week 53 is dropped.** In this dataset it is a partial-week bucket, not a real
  epidemiological week: it averages ~36k national attentions against ~104k for a normal
  week. Keeping it injects a spurious 65% demand collapse once a year.
* **Pollution weeks are ISO weeks.** The DEIS file gives only (Anio, SemanaEstadistica) with
  no date column, so the exact PAHO/MMWR week boundaries cannot be recovered from it. ISO
  weeks may sit up to a few days off. That offset is constant, so it shifts the lag structure
  rather than distorting it — which is why every analysis downstream scans a lag range
  instead of trusting lag 0.
* **Exposure is summarised two ways.** Weekly `mean` is the standard exposure metric;
  weekly `max` of the daily series captures acute peaks, which is the mechanism that would
  plausibly drive an emergency visit. Both are returned.
"""

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WEEKLY_PARQUET = (
    ROOT / "data" / "raw" / "Atenciones de Urgencia"
    / "Atenciones de urgencias de causas respiratorias por semana epidemiológica"
    / "at_urg_respiratorio_semanal.parquet"
)
SINCA_PARQUET = ROOT / "data" / "processed" / "sinca_aire" / "sinca_2023_2025_diario.parquet"

TARGET_ORDEN_CAUSA = 3  # TOTAL CAUSA SISTEMA RESPIRATORIO (J00-J98)
HOSPITALIZATION_ORDEN_CAUSA = 33  # "- Causas sistema respiratorio" — NOT the target
EARTH_RADIUS_KM = 6371.0

# Facilities carry free-text metadata with whitespace and case variants that would otherwise
# fragment a category in two ("Municipal" / "Municipal ", 418 vs 13 facilities).
PLACEHOLDER_CATEGORIES = {"completar", "pendiente", "no aplica", "", "nan", "none"}
CATEGORICAL_COLS = [
    "RegionGlosa", "ComunaGlosa", "ServicioSaludGlosa", "TipoEstablecimiento",
    "DependenciaAdministrativa", "NivelAtencion", "TipoUrgencia", "NivelComplejidad",
]


def normalize_category(series):
    """Collapse whitespace/case variants and turn placeholders into NA."""
    s = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    return s.mask(s.str.lower().isin(PLACEHOLDER_CATEGORIES))


def _to_float(series):
    """DEIS writes coordinates as '-38,235162' — comma decimal separator."""
    return pd.to_numeric(
        series.astype("string").str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )


def load_weekly_target(year_min=None, year_max=None, con=None):
    """One row per (facility, year, epidemiological week) with static metadata attached.

    Returns the target `Total_Respiratorias` plus the age breakdown. Note the age columns
    sum to the total exactly, so never feed both to a model — see decisions/log.md.
    """
    where = [f"OrdenCausa = {TARGET_ORDEN_CAUSA}", "SemanaEstadistica <> 53"]
    if year_min is not None:
        where.append(f"Anio >= {year_min}")
    if year_max is not None:
        where.append(f"Anio <= {year_max}")

    query = f"""
    SELECT
        EstablecimientoCodigo, EstablecimientoGlosa,
        RegionGlosa, ComunaGlosa, ServicioSaludGlosa, TipoEstablecimiento,
        DependenciaAdministrativa, NivelAtencion, TipoUrgencia, NivelComplejidad,
        Latitud, Longitud,
        Anio, SemanaEstadistica,
        SUM(NumTotal)      AS Total_Respiratorias,
        SUM(NumMenor1Anio) AS Menores_1,
        SUM(Num1a4Anios)   AS De_1_a_4,
        SUM(Num5a14Anios)  AS De_5_a_14,
        SUM(Num15a64Anios) AS De_15_a_64,
        SUM(Num65oMas)     AS De_65_y_mas
    FROM read_parquet('{WEEKLY_PARQUET.as_posix()}')
    WHERE {' AND '.join(where)}
    GROUP BY ALL
    """
    con = con or duckdb.connect()
    df = con.execute(query).df()

    df["Latitud"] = _to_float(df["Latitud"])
    df["Longitud"] = _to_float(df["Longitud"])
    for c in CATEGORICAL_COLS:
        df[c] = normalize_category(df[c])

    # 2020-2021 ER demand collapsed ~65% and ~51% under COVID restrictions, then overshot
    # in 2022. A model spanning those years needs the regime to be observable.
    df["covid_regime"] = np.select(
        [df["Anio"].isin([2020, 2021]), df["Anio"] == 2022],
        ["restriction", "rebound"],
        default="normal",
    )
    return df


def load_weekly_pollution(con=None):
    """Station × ISO-week air quality: mean and max of the daily series, per pollutant."""
    query = f"""
    SELECT
        estacion, region,
        any_value(latitud)  AS latitud,
        any_value(longitud) AS longitud,
        pollutant,
        -- ISOYEAR, not YEAR: DuckDB's WEEK() is the ISO week, and at a year boundary the
        -- two disagree (2024-12-30 is ISO week 1 of *2025*). Pairing the calendar year with
        -- an ISO week silently joins December pollution to January demand.
        CAST(ISOYEAR(fecha) AS INTEGER) AS iso_year,
        CAST(WEEK(fecha) AS INTEGER)    AS iso_week,
        AVG(valor)   AS valor_mean,
        MAX(valor)   AS valor_max,
        COUNT(valor) AS dias_observados
    FROM read_parquet('{SINCA_PARQUET.as_posix()}')
    GROUP BY estacion, region, pollutant, iso_year, iso_week
    """
    con = con or duckdb.connect()
    df = con.execute(query).df()
    return df[df["iso_week"] != 53]


def nearest_station(facilities, stations, max_km=None):
    """Map each facility to its nearest monitoring station.

    Lat/lon degrees are not a metric space, so coordinates are projected onto 3D Cartesian
    points on a sphere of Earth's radius; Euclidean distance there approximates the
    great-circle arc closely at these scales, which lets a KD-tree do the search in
    milliseconds. Chord length is converted back to arc length so the reported km are real
    surface distances.
    """
    from scipy.spatial import cKDTree

    def to_xyz(lat, lon):
        lat, lon = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
        return np.column_stack([
            EARTH_RADIUS_KM * np.cos(lat) * np.cos(lon),
            EARTH_RADIUS_KM * np.cos(lat) * np.sin(lon),
            EARTH_RADIUS_KM * np.sin(lat),
        ])

    fac = facilities.dropna(subset=["Latitud", "Longitud"]).copy()
    sta = stations.dropna(subset=["latitud", "longitud"]).copy()

    tree = cKDTree(to_xyz(sta["latitud"], sta["longitud"]))
    chord, idx = tree.query(to_xyz(fac["Latitud"], fac["Longitud"]), k=1)

    # chord -> arc: d_arc = 2R * arcsin(chord / 2R)
    fac["nearest_station"] = sta["estacion"].to_numpy()[idx]
    fac["station_distance_km"] = 2 * EARTH_RADIUS_KM * np.arcsin(
        np.clip(chord / (2 * EARTH_RADIUS_KM), -1, 1)
    )
    if max_km is not None:
        fac = fac[fac["station_distance_km"] <= max_km]
    return fac


def build_weekly_panel(pollutant="mp2.5", max_km=25, min_days=4, con=None):
    """The analytical table: weekly demand per facility with its exposure series attached.

    `min_days` guards the weekly exposure summary — a week represented by one or two daily
    readings is noise, not an average.
    """
    con = con or duckdb.connect()
    target = load_weekly_target(2023, 2025, con=con)
    pollution = load_weekly_pollution(con=con)
    pollution = pollution[
        (pollution["pollutant"] == pollutant) & (pollution["dias_observados"] >= min_days)
    ]

    facilities = (
        target.groupby("EstablecimientoCodigo", as_index=False)
        .agg(Latitud=("Latitud", "first"), Longitud=("Longitud", "first"))
    )
    stations = pollution.groupby("estacion", as_index=False).agg(
        latitud=("latitud", "first"), longitud=("longitud", "first")
    )
    linked = nearest_station(facilities, stations, max_km=max_km)

    panel = (
        target.merge(
            linked[["EstablecimientoCodigo", "nearest_station", "station_distance_km"]],
            on="EstablecimientoCodigo", how="inner",
        )
        .merge(
            pollution[["estacion", "iso_year", "iso_week", "valor_mean", "valor_max"]],
            left_on=["nearest_station", "Anio", "SemanaEstadistica"],
            right_on=["estacion", "iso_year", "iso_week"],
            how="inner",
        )
        .drop(columns=["estacion", "iso_year", "iso_week"])
        .rename(columns={"valor_mean": f"{pollutant}_mean", "valor_max": f"{pollutant}_max"})
    )
    return panel.sort_values(["EstablecimientoCodigo", "Anio", "SemanaEstadistica"])


def deseasonalize(df, value_col, group_col="EstablecimientoCodigo", week_col="SemanaEstadistica"):
    """Return the anomaly: value minus its own facility's week-of-year climatology.

    This is the whole methodological point. Respiratory demand and particulate pollution
    both peak in the southern winter, so their raw correlation largely measures "winter
    resembles winter". Subtracting each series' seasonal profile leaves the deviations, and
    only a correlation that survives that is evidence of a real association.
    """
    climatology = df.groupby([group_col, week_col])[value_col].transform("mean")
    return df[value_col] - climatology


def demo():
    """Self-check on the invariants this module depends on."""
    assert normalize_category(pd.Series(["Municipal", "Municipal ", " municipal"])).nunique() == 2, \
        "whitespace variants should collapse, case should not"
    assert normalize_category(pd.Series(["Completar", "Pendiente"])).isna().all(), \
        "placeholders must become NA"
    assert _to_float(pd.Series(["-38,235162"])).iloc[0] == -38.235162

    # Distance sanity: Santiago -> Valparaiso is ~100 km great-circle.
    fac = pd.DataFrame({"EstablecimientoCodigo": ["X"], "Latitud": [-33.45], "Longitud": [-70.66]})
    sta = pd.DataFrame({"estacion": ["V"], "latitud": [-33.05], "longitud": [-71.62]})
    d = nearest_station(fac, sta)["station_distance_km"].iloc[0]
    assert 90 < d < 110, f"great-circle distance looks wrong: {d:.1f} km"

    df = load_weekly_target(2023, 2025)
    assert (df["SemanaEstadistica"] != 53).all(), "week 53 leaked through"
    assert not df.duplicated(["EstablecimientoCodigo", "Anio", "SemanaEstadistica"]).any()
    resid = df["Total_Respiratorias"] - df[
        ["Menores_1", "De_1_a_4", "De_5_a_14", "De_15_a_64", "De_65_y_mas"]
    ].sum(axis=1)
    assert (resid == 0).all(), "age bands should reconstruct the total exactly"

    # Deseasonalized anomalies must be centred on zero within each facility-week cell.
    df["anom"] = deseasonalize(df, "Total_Respiratorias")
    assert abs(df["anom"].mean()) < 1e-6, "anomalies are not centred"

    print(f"OK  weekly target: {len(df):,} rows · "
          f"{df['EstablecimientoCodigo'].nunique()} facilities · "
          f"{df['Anio'].min()}-{df['Anio'].max()}, distance check {d:.1f} km")


if __name__ == "__main__":
    demo()
