"""Canonical loaders for the VitalFlow analytical datasets.

The target definition lives here and nowhere else. It was previously copy-pasted into
notebooks and scratch scripts, and the copies silently disagreed: filtering causes with
``GlosaCausa LIKE '%RESPIRATORIO%'`` matches IdCausa 2 *and* IdCausa 7, which belong to
two different sections of the DEIS report (ER attentions vs. hospitalizations). Import
from here instead of rewriting the query.

Cause taxonomy (DEIS), verified against the data:

    SECCION 1 -- IdCausa 1  TOTAL ATENCIONES DE URGENCIA
      IdCausa 2   TOTAL CAUSAS SISTEMA RESPIRATORIO   <-- the target
        IdCausa 3   Bronquitis/bronquiolitis aguda (J20-J21)
        IdCausa 4   Influenza (J09-J11)
        IdCausa 5   Neumonia (J12-J18)
        IdCausa 6   Otra causa respiratoria (J22, J30-J39, J47, J60-J98)
        IdCausa 10  IRA Alta (J00-J06)
        IdCausa 11  Crisis obstructiva bronquial (J40-J46)
    SECCION 2 -- IdCausa 25 TOTAL DE HOSPITALIZACIONES
      IdCausa 7   CAUSAS SISTEMA RESPIRATORIO         <-- severity, NOT the target
"""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
URGENCIAS_GLOB = str(ROOT / "data" / "processed" / "urgencias_parquet" / "*.parquet")
MAPPING_CSV = ROOT / "data" / "processed" / "hospital_sinca_dmc_mapping.csv"

TARGET_CAUSE = 2  # TOTAL CAUSAS SISTEMA RESPIRATORIO (ER attentions)
SEVERITY_CAUSE = 7  # CAUSAS SISTEMA RESPIRATORIO (hospitalizations)
RESPIRATORY_SUBCAUSES = {
    3: "Bronquitis",
    4: "Influenza",
    5: "Neumonia",
    6: "Otra_respiratoria",
    10: "IRA_Alta",
    11: "Crisis_obstructiva",
}

AGE_COLS = ["Menores_1", "De_1_a_4", "De_5_a_14", "De_15_a_64", "De_65_y_mas"]


def repair_mojibake(text):
    """Undo UTF-8 bytes that were decoded as latin-1 ("MÃ©dico" -> "Médico").

    Returns the input untouched when it is not double-encoded, so this is safe to
    apply to a whole column regardless of which rows are damaged.
    """
    if not isinstance(text, str):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def load_target(by_age=True, con=None):
    """Daily respiratory ER attentions per health facility, 2017-2024.

    One row per (fecha, IdEstablecimiento). Out-of-core via DuckDB — the raw CSVs
    behind these Parquet files exceed available RAM.
    """
    age_select = ",\n        ".join(f"SUM({c}) AS {c}" for c in AGE_COLS) if by_age else ""
    query = f"""
    SELECT
        strptime(fecha, '%d/%m/%Y') AS fecha,
        IdEstablecimiento,
        any_value(NEstablecimiento) AS NEstablecimiento,
        SUM(Total) AS Total_Respiratorias{"," if age_select else ""}
        {age_select}
    FROM read_parquet('{URGENCIAS_GLOB}')
    WHERE IdCausa = {TARGET_CAUSE}
    GROUP BY fecha, IdEstablecimiento
    ORDER BY fecha, IdEstablecimiento
    """
    con = con or duckdb.connect()
    df = con.execute(query).df()
    return df.dropna(subset=["fecha"])


def load_subcauses(con=None):
    """Daily counts broken down by respiratory sub-cause, wide format.

    These six columns sum to `Total_Respiratorias`, so never feed them to a model
    together with the total — that is perfect multicollinearity by construction.
    """
    cases = ",\n        ".join(
        f"SUM(CASE WHEN IdCausa = {cid} THEN Total ELSE 0 END) AS {name}"
        for cid, name in RESPIRATORY_SUBCAUSES.items()
    )
    query = f"""
    SELECT
        strptime(fecha, '%d/%m/%Y') AS fecha,
        IdEstablecimiento,
        {cases},
        SUM(CASE WHEN IdCausa = {SEVERITY_CAUSE} THEN Total ELSE 0 END) AS Hospitalizaciones_Resp
    FROM read_parquet('{URGENCIAS_GLOB}')
    WHERE IdCausa IN ({','.join(str(c) for c in RESPIRATORY_SUBCAUSES)}, {SEVERITY_CAUSE})
    GROUP BY fecha, IdEstablecimiento
    ORDER BY fecha, IdEstablecimiento
    """
    con = con or duckdb.connect()
    df = con.execute(query).df()
    return df.dropna(subset=["fecha"])


def load_mapping(max_sinca_km=None, max_dmc_km=None):
    """Facility -> nearest SINCA / DMC station, with names repaired.

    Distances are the honest measure of how much an exogenous series actually says
    about a facility: the raw table reaches 3,509 km, which is a bad coordinate rather
    than a real neighbour. Pass a threshold to drop pairings you do not trust.
    """
    df = pd.read_csv(MAPPING_CSV)
    for col in ("EstablecimientoGlosa", "nearest_sinca_station", "nearest_dmc_station"):
        if col in df.columns:
            df[col] = df[col].map(repair_mojibake)
    if max_sinca_km is not None:
        df = df[df["distance_to_sinca_km"] <= max_sinca_km]
    if max_dmc_km is not None:
        df = df[df["distance_to_dmc_km"] <= max_dmc_km]
    return df


def demo():
    """Self-check: the taxonomy assumptions this module is built on must hold."""
    con = duckdb.connect()
    parent, children, severity = con.execute(
        f"""
        SELECT
            SUM(CASE WHEN IdCausa = {TARGET_CAUSE} THEN Total END) AS parent,
            SUM(CASE WHEN IdCausa IN ({','.join(str(c) for c in RESPIRATORY_SUBCAUSES)})
                     THEN Total END) AS children,
            SUM(CASE WHEN IdCausa = {SEVERITY_CAUSE} THEN Total END) AS severity
        FROM read_parquet('{URGENCIAS_GLOB}')
        """
    ).fetchone()
    drift = abs(parent - children) / parent
    assert drift < 1e-4, f"sub-causes do not reconstruct the total (drift={drift:.2%})"
    assert severity < parent, "hospitalizations should be a fraction of ER attentions"

    df = load_target()
    assert df["fecha"].notna().all(), "unparsed dates leaked through"
    assert not df.duplicated(["fecha", "IdEstablecimiento"]).any(), "target not unique per panel cell"
    assert (df["Total_Respiratorias"] >= 0).all(), "negative counts"

    assert repair_mojibake("Servicio MÃ©dico Legal") == "Servicio Médico Legal"
    assert repair_mojibake("Hospital Regional") == "Hospital Regional"  # untouched
    assert repair_mojibake(None) is None

    print(f"OK  target={parent:,.0f}  subcauses={children:,.0f}  drift={drift:.2e}")
    print(f"OK  panel: {len(df):,} rows, {df['IdEstablecimiento'].nunique()} facilities")


if __name__ == "__main__":
    demo()
