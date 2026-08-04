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
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.data.refresh import RELEASE  # noqa: E402
from src.models.train_model import (  # noqa: E402
    ALERT_LIST, ALERT_LIST_LIVE, BASELINE_TRAIN_FROM, FORECAST, SURGE_QUANTILE, Y,
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


def release_stamp(panel):
    """AC-I9: which week is being served, and when this export was produced.

    `settled_through` is the load-bearing half. It is read off the panel that was actually
    exported, so it cannot claim to be fresher than the data -- and if the refresh job stops it
    freezes, which is exactly the signal a coordinator needs to tell "no risk" from "the pipeline
    died". `published` is DEIS's own date and is absent when the parquet was placed on disk by
    hand; `stamp` is this run, and it is what visibly ages on screen.
    """
    year = int(panel["Anio"].max())
    week = int(panel.loc[panel["Anio"] == year, "SemanaEstadistica"].max())
    published = json.loads(RELEASE.read_text(encoding="utf-8")).get("published") \
        if RELEASE.exists() else None
    return {"stamp": date.today().isoformat(), "settled_through": [year, week],
            "published": published}


def _empty_season():
    """A function, not a module constant: a shared dict would hand every facility with no scored
    row the SAME nested lists."""
    return {"weeks": [], "attentions": [], "surge": [], "onset": [],
            "h1": {"alert": [], "rank": []}, "h2": {"alert": [], "rank": []}}


def season_payload(code, g, obs, p90):
    """One facility's season as parallel arrays, keyed by epidemiological week.

    Shared by the retrospective export and the live one. A facility with no scored row in the
    season returns empty arrays rather than raising: on the live screen that is a real state
    (AC-I8) and it must reach the browser as data, not as a 404.
    """
    if g.empty:
        return {"code": code, "p90": p90, **_empty_season()}
    weeks = sorted(g["week"].unique())
    by_h = {int(h): hg.set_index("week") for h, hg in g.groupby("horizon")}
    h2 = by_h.get(2, by_h[min(by_h)])                     # the horizon that deploys
    return {
        "code": code, "p90": p90,
        "weeks": [int(w) for w in weeks],
        "attentions": [_int_or_none(obs.get((code, w))) for w in weeks],
        "surge": [int(bool(h2["observed_surge"].get(w, False))) for w in weeks],
        "onset": [int(bool(h2["observed_onset"].get(w, False))) for w in weeks],
        **{f"h{h}": {"alert": [int(bool(d["alert"].get(w, False))) for w in weeks],
                     "rank": [int(d["rank"].get(w, 0)) for w in weeks]}
           for h, d in by_h.items()},
    }


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
        payload = {**season_payload(code, g, obs, round(float(thr.get(code, float("nan"))), 1)),
                   "season": season,
                   # AC-E7: the outcome arrays above exist only because the season is over.
                   "retrospective": True}
        payload.update({k: _clean(v) for k, v in meta.loc[code].items()})
        payloads[code] = payload

        h2 = g[g["horizon"] == 2] if (g["horizon"] == 2).any() else g
        index.append({
            "code": code, **{k: _clean(v) for k, v in meta.loc[code].items()},
            "weeks": len(payload["weeks"]),
            "alerts": int(h2["alert"].sum()),      # h=2 — the operational horizon
            "surges": int(h2["observed_surge"].sum()),
        })

    return ({"season": season, "retrospective": True, **release_stamp(panel),
             "facilities": index}, payloads)


def build_live(alerts_path=ALERT_LIST_LIVE, forecast_path=FORECAST):
    """The current season to date, plus the model's claim about a week that has not happened.

    One file per hospital ER, **including the ones with no claim**: some facilities get no forecast
    row because they are missing the origin week or one of its lags, and a missing file would
    render as an error where AC-I8 requires `sin dato`. The claim carries its own `stamp` rather
    than borrowing the index's -- a statement about the future should date itself.
    """
    alerts = pd.read_parquet(alerts_path)
    fc = pd.read_parquet(forecast_path)
    season = int(alerts["year"].iloc[0])
    assert alerts["year"].nunique() == 1, "one season per live export"
    assert (fc["year"] == season).all(), \
        f"the forecast targets {sorted(fc['year'].unique())} but the season on disk is {season}"

    panel = load_panel()
    panel = panel[panel["EstablecimientoCodigo"].isin(hospital_er_facilities(panel))]
    thr = surge_thresholds(panel, season)
    meta = panel.groupby("EstablecimientoCodigo")[list(META)].first().rename(columns=META)
    obs = (panel[panel["Anio"] == season]
           .set_index(["EstablecimientoCodigo", "SemanaEstadistica"])[Y])

    # The ordinal, and it is the only quantity about the target week the interface may show.
    # Ranked over the season's OWN scored weeks with the claim among them, so "2a de 31" means
    # "the second-highest of the thirty-one weeks of this season this service has been scored on".
    key = ["facility", "horizon", "week"]
    both = pd.concat([alerts[[*key, "score"]].assign(claim=False),
                      fc[[*key, "score"]].assign(claim=True)], ignore_index=True)
    grp = both.groupby(["facility", "horizon"])["score"]
    both["rank"] = grp.rank(ascending=False, method="min").astype(int)
    both["of"] = grp.transform("size").astype(int)

    # The observed weeks are ranked in the SAME universe as the claim, not separately. Two
    # denominators in one payload is how "2a de 31" quietly stops meaning what the caption says.
    n = len(alerts)
    alerts = alerts.drop(columns="rank", errors="ignore").merge(
        both.loc[~both["claim"], [*key, "rank"]], on=key)
    assert len(alerts) == n, \
        "the rank merge changed the row count -- the alert list is not one row per facility/horizon/week"
    claims = both[both["claim"]].merge(fc[["facility", "horizon", "alert"]],
                                       on=["facility", "horizon"])

    stamp = date.today().isoformat()
    origin = [int(fc["origin_year"].iloc[0]), int(fc["origin_week"].iloc[0])]
    payloads = {}
    for code in sorted(panel["EstablecimientoCodigo"].unique()):
        g = alerts[alerts["facility"] == code]
        c = claims[claims["facility"] == code].sort_values("horizon")
        payload = {
            **season_payload(code, g, obs, round(float(thr.get(code, float("nan"))), 1)),
            "season": season, "retrospective": False, "stamp": stamp, "origin": origin,
            "forecast": [{"horizon": int(r.horizon), "week": int(r.week),
                          "alert": int(bool(r.alert)), "rank": int(r.rank), "of": int(r.of)}
                         for r in c.itertuples()],
        }
        payload.update({k: _clean(v) for k, v in meta.loc[code].items()})
        payloads[code] = payload
    return payloads


def export_live(out=OUT):
    """Write one live file per facility. Returns the directory written."""
    payloads = build_live()
    (out / "live").mkdir(parents=True, exist_ok=True)
    for code, payload in payloads.items():
        _write(out / "live" / f"{code}.json", payload)
    claimed = sum(1 for p in payloads.values() if p["forecast"])
    print(f"OK  live · {len(payloads)} facilities, {claimed} with a forecast · "
          f"origin {payloads[next(iter(payloads))]['origin']}")
    return out / "live"


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
    # AC-I9: nothing on screen can go silently stale. The screen reads these three and nothing else.
    assert index["stamp"] and index["settled_through"], "the export carries no AC-I9 stamp"
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

    # The live export, and the things that can silently go wrong in it.
    live = {p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((out / "live").glob("*.json"))}
    assert live.keys() >= codes, "a facility has no live file -- its route would 404, not say `sin dato`"
    for code, p in live.items():
        assert "score" not in json.dumps(p), f"{code}: a score leaked into the live export"
        assert p["retrospective"] is False, f"{code}: the live payload claims to be retrospective"
        # `summarize()` reads `h2` on every payload; a partial season missing that horizon would
        # reach the browser as a blank screen rather than as any of the four designed states.
        assert "h2" in p, f"{code}: the live payload carries no h=2 horizon"
        for c in p["forecast"]:
            # The whole point of the file: the claim must be about a week nobody has seen.
            assert c["week"] > p["origin"][1], \
                f"{code}: claimed week {c['week']} is not past the origin week {p['origin'][1]}"
            assert c["week"] not in p["weeks"], \
                f"{code}: week {c['week']} is claimed AND observed -- that is a backtest row"
            assert 1 <= c["rank"] <= c["of"], f"{code}: rank {c['rank']} of {c['of']}"

    silent = [c for c, p in live.items() if not p["forecast"]]
    print(f"OK  live · {len(live)} facilities · {len(live) - len(silent)} with a claim · "
          f"{len(silent)} with none (AC-I8 `sin dato`): {silent}")


if __name__ == "__main__":
    export()
    demo()
