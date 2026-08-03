"""Static JSON for the facility explorer: no backend, no API, no database.

Reads `data/processed/alert_list.parquet` (what the model served) and the weekly panel (what
actually happened), and writes one small index plus one file per hospital ER. A read-only viewer
over ~18k rows does not justify reintroducing the Redis + FastAPI design the decision log deleted
on 2026-07-27.

Spec: `context/specs/facility-explorer.md`. Two shape decisions are load-bearing and are made here
rather than in the components:

* **`score` is never exported.** Only a rank within the facility's own season. Calibration was
  measured and rejected (2026-07-29), so a probability would be dishonest — and a column the file
  does not contain cannot be rendered by mistake. AC-E2 and AC-I2 hold by construction.
* **Parallel arrays, not an array of objects.** 52 weeks x 2 horizons per facility, and the ribbon
  and the series both iterate by week index. Keeps each file a few KB.

The outcome columns exist because the season is over. **In deployment they are blank for the target
week** — that is the entire point of a forecast. AC-E7 requires the interface to say so; the
`retrospective` flag below is what it reads.
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.models.train_model import (  # noqa: E402
    ALERT_LIST, BASELINE_TRAIN_FROM, SURGE_QUANTILE, Y,
    hospital_er_facilities, load_panel, train_years_for,
)

OUT = ROOT / "frontend" / "public" / "data"
META = {
    "EstablecimientoGlosa": "name", "ComunaGlosa": "comuna", "RegionGlosa": "region",
    "TipoUrgencia": "type", "NivelComplejidad": "complexity",
}


def surge_thresholds(panel, season):
    """Each facility's p90, computed from the same rows `alert_frame` labels the season against.

    Not a re-derivation for display: `demo()` asserts the parquet's `observed_surge` equals
    `attentions > threshold` on every scored row, so a drift between this and the model's own
    threshold fails the check rather than silently mislabelling the ribbon.
    """
    seasons = train_years_for(panel, season, since=BASELINE_TRAIN_FROM)
    rank_rows = panel[panel["Anio"].isin(seasons)]
    return rank_rows.groupby("EstablecimientoCodigo")[Y].quantile(SURGE_QUANTILE)


def build(path=ALERT_LIST):
    """Returns `(index, {code: payload})` — everything the explorer needs, still in memory."""
    alerts = pd.read_parquet(path)
    season = int(alerts["year"].iloc[0])
    assert alerts["year"].nunique() == 1, "one season per export; re-run write_alert_list per year"

    panel = load_panel()
    panel = panel[panel["EstablecimientoCodigo"].isin(hospital_er_facilities(panel))]
    thr = surge_thresholds(panel, season)
    meta = panel.groupby("EstablecimientoCodigo")[list(META)].first().rename(columns=META)

    obs = (panel[panel["Anio"] == season]
           .set_index(["EstablecimientoCodigo", "SemanaEstadistica"])[Y])

    # Rank within the facility's own season, per horizon: 1 = the week it was most at risk. This is
    # the only ordinal the interface may show (AC-I2) and the only thing `score` survives as.
    alerts["rank"] = (alerts.groupby(["facility", "horizon"])["score"]
                      .rank(ascending=False, method="min").astype(int))

    index, payloads = [], {}
    for code, g in alerts.groupby("facility", sort=True):
        weeks = sorted(g["week"].unique())
        by_week = {h: hg.set_index("week") for h, hg in g.groupby("horizon")}
        h2 = by_week.get(2, by_week[min(by_week)])          # the horizon that deploys

        payload = {
            "code": code, "season": season,
            # AC-E7: the outcome arrays below exist only because the season is over.
            "retrospective": True,
            "p90": round(float(thr.get(code, float("nan"))), 1),
            "weeks": [int(w) for w in weeks],
            "attentions": [_int_or_none(obs.get((code, w))) for w in weeks],
            "surge": [int(bool(h2["observed_surge"].get(w, False))) for w in weeks],
            "onset": [int(bool(h2["observed_onset"].get(w, False))) for w in weeks],
            **{f"h{h}": {"alert": [int(bool(d["alert"].get(w, False))) for w in weeks],
                         "rank": [int(d["rank"].get(w, 0)) for w in weeks]}
               for h, d in by_week.items()},
        }
        payload.update({k: _clean(v) for k, v in meta.loc[code].items()})
        payloads[code] = payload

        index.append({
            "code": code, **{k: _clean(v) for k, v in meta.loc[code].items()},
            "weeks": len(weeks),
            "alerts": int(h2["alert"].sum()),      # h=2 — the operational horizon
            "surges": int(h2["observed_surge"].sum()),
        })

    return {"season": season, "retrospective": True, "facilities": index}, payloads


def _int_or_none(v):
    return None if v is None or pd.isna(v) else int(v)


def _clean(v):
    return None if pd.isna(v) else str(v)


def export(out=OUT):
    """Write the index and one file per facility. Returns the paths written."""
    index, payloads = build()
    (out / "facility").mkdir(parents=True, exist_ok=True)
    _write(out / "facilities.json", index)
    for code, payload in payloads.items():
        _write(out / "facility" / f"{code}.json", payload)
    print(f"OK  {len(payloads)} facilities · season {index['season']} · "
          f"index {(out / 'facilities.json').stat().st_size / 1024:.0f} KB · "
          f"largest facility {max((out / 'facility' / f'{c}.json').stat().st_size for c in payloads) / 1024:.1f} KB")
    return out


def _write(path, obj):
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def demo(out=OUT):
    """AC-E5: the exported JSON matches the parquet. Reads what was actually written to disk."""
    alerts = pd.read_parquet(ALERT_LIST)
    index = json.loads((out / "facilities.json").read_text(encoding="utf-8"))
    codes = set(alerts["facility"].unique())

    assert {f["code"] for f in index["facilities"]} == codes, "index and parquet disagree on facilities"
    # AC-E6: first paint loads the index only, so the index must carry no per-week data.
    assert not any(isinstance(v, list) for f in index["facilities"] for v in f.values()), \
        "the index carries a series -- first paint would load every facility's weeks"

    panel = load_panel()
    thr = surge_thresholds(panel, int(alerts["year"].iloc[0]))
    checked = 0
    for code in sorted(codes):
        p = json.loads((out / "facility" / f"{code}.json").read_text(encoding="utf-8"))
        g = alerts[alerts["facility"] == code]
        assert len(p["weeks"]) == g["week"].nunique(), f"{code}: week count differs from the parquet"
        assert "score" not in json.dumps(p), f"{code}: a score leaked into the export"

        # The end-to-end check: the model's own surge label must equal attentions > this p90.
        # If `surge_thresholds` ever drifts from `alert_frame`, this is what catches it.
        for w, n, s in zip(p["weeks"], p["attentions"], p["surge"]):
            if n is not None:
                assert (n > p["p90"]) == bool(s), f"{code} w{w}: {n} vs p90 {p['p90']} != surge {s}"
                checked += 1

    # AC-E9: facility 129103 must be inspectable AND its disagreements must survive the export -- a
    # viewer that cannot show a surge nobody was warned about is not an honest viewer.
    # The audit of 2026-07-30 called 129103 "zero alerts in three seasons" and this file carries
    # one -- in week 50, outside the audit's matched weeks 1-28 window. Both are correct. Its three
    # real surges are weeks 19, 21 and 33: the model's single 2025 alert lands in December, months
    # after the respiratory season it missed. That is the failure the explorer has to render.
    miss = json.loads((out / "facility" / "129103.json").read_text(encoding="utf-8"))
    missed = [w for w, s, a in zip(miss["weeks"], miss["surge"], miss["h2"]["alert"]) if s and not a]
    assert missed, "129103: no un-alerted surge survived the export -- the viewer cannot show a miss"

    print(f"OK  {len(codes)} facilities · {checked:,} facility-weeks reconciled against the parquet "
          f"· 129103: {sum(miss['surge'])} surges, {sum(miss['h2']['alert'])} alerts at h=2, "
          f"{len(missed)} surge week(s) nobody was warned about (weeks {missed})")


if __name__ == "__main__":
    export()
    demo()
