"""The weekly refresh: pull the DEIS release, re-run the alert list, the forecast and the export.

`context/specs/alert-interface.md` AC-I9. Run it from cron, Task Scheduler or a CI workflow --
**not** from a service. The decision log deleted the Redis + FastAPI design on 2026-07-27 because a
CPU model refreshed weekly does not need one, and building a service to run a weekly batch would be
that mistake a second time.

**This job does not implement "refuse to serve a short week" -- `load_weekly_target` already does.**
A DEIS week is 19.1% complete the day it closes, and `drop_unsettled_tail` trims it, so the pipeline
*cannot* serve one. What was missing is making visible WHICH week is served. A coordinator looking
at 29 silent weeks has to be able to tell "no risk" from "the pipeline died" (silent-facility audit,
2026-07-30) and no number already on the screen distinguishes them. That is the stamp this job
writes, and it is the whole point of the job.

The download is the only step that can lose data, so it is the only step carrying guards: the
candidate is validated in a temp file and the served parquet is replaced only after it passes.

    venv/Scripts/python.exe src/data/refresh.py            # pull if new, then re-export
    venv/Scripts/python.exe src/data/refresh.py --force    # re-export from what is on disk
    venv/Scripts/python.exe src/data/refresh.py --check    # the self-check, no network
"""

import json
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.features.build_features import (  # noqa: E402
    TARGET_ORDEN_CAUSA, WEEKLY_PARQUET,
)

# `sources/index.md` §1. WebFetch on minsal.cl returns 403; the CKAN API does not.
CKAN_API = "https://datos.gob.cl/api/3/action/resource_show?id={}"
CKAN_RESOURCE = "ae6c9887-106d-4e98-8875-40bf2b836041"

# Written here, read by `export_frontend.release_stamp`. A file rather than the parquet's mtime:
# copying the parquet resets its mtime *forward*, which would make a stale export look fresh --
# the one direction a staleness indicator must never fail in.
RELEASE = ROOT / "data" / "processed" / "deis_release.json"

# DEIS back-revises months of history, so a genuine release is never much smaller than the last
# one. A truncated download is not: it reads as a demand collapse, silently and in the direction
# that makes a surge model predict calm.
MIN_ROW_RATIO = 0.95


def release():
    """What CKAN says the current release is: publication date, download URL, size."""
    with urllib.request.urlopen(CKAN_API.format(CKAN_RESOURCE), timeout=60) as r:
        d = json.load(r)["result"]
    return {
        "published": d.get("last_modified") or d["metadata_modified"],
        "url": d["url"],
        "size": d.get("size"),
    }


def fetch(url, dest, timeout=600):
    """Stream to `dest`. The file is ~67 MB -- never read it into memory."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=timeout) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    return dest


def coverage(path):
    """`(rows, (year, week))` for the target cause. Raises if the file is not the expected shape.

    **Week 53 is excluded, exactly as `load_weekly_target` excludes it.** DEIS keeps a week-53
    bucket -- 639 facilities and 24,492 attentions in 2026 -- and counting it made this function
    report `(2026, 53)` for every snapshot ever published. The backwards guard below compares that
    number, so with week 53 in it the guard compared 5353 against 5353 and could not fail: a
    snapshot that rolled back from week 28 to week 20 would have installed silently. Found by
    running the download against the served file, not by any test (rule 25).
    """
    rows, newest = duckdb.connect().execute(f"""
        SELECT COUNT(*), MAX(Anio * 100 + SemanaEstadistica)
        FROM read_parquet('{Path(path).as_posix()}')
        WHERE OrdenCausa = {TARGET_ORDEN_CAUSA} AND SemanaEstadistica <> 53
    """).fetchone()
    assert rows, f"{path}: no OrdenCausa = {TARGET_ORDEN_CAUSA} rows -- wrong file or wrong schema"
    return int(rows), (int(newest) // 100, int(newest) % 100)


def validate(candidate, current):
    """Refuse a candidate that is worse than what is already served. Returns its `(rows, week)`.

    Both failure modes are silent if unguarded -- DuckDB reads a truncated parquet happily, and a
    re-published older snapshot rolls the served week backwards without any error at all.
    """
    new_rows, new_week = coverage(candidate)
    if not Path(current).exists():
        return new_rows, new_week

    old_rows, old_week = coverage(current)
    assert new_week >= old_week, \
        f"candidate ends at week {new_week} against {old_week} on disk -- it goes backwards"
    assert new_rows >= old_rows * MIN_ROW_RATIO, \
        f"candidate has {new_rows:,} rows against {old_rows:,} on disk -- truncated download?"
    return new_rows, new_week


def install(candidate, dest):
    """Replace `dest`, keeping the previous file as `.bak` until the next successful refresh."""
    if dest.exists():
        dest.replace(dest.with_suffix(dest.suffix + ".bak"))
    candidate.replace(dest)


def served_season(default):
    """The season `alert_list.parquet` is currently built for, or `default` if there is none."""
    from src.models.train_model import ALERT_LIST
    if not ALERT_LIST.exists():
        return default
    return int(pd.read_parquet(ALERT_LIST, columns=["year"])["year"].iloc[0])


def rebuild(season=None):
    """Re-run the alert list and the static export over whatever is now on disk.

    **`season` defaults to the one already being served, not to the newest year in the panel.**
    Refreshing data must not decide which season is on screen: rolling the explorer from a finished
    2025 to a partial 2026 changes what the product *is*, and that belongs to the live-screen work
    (`alert-interface.md` AC-I7/I8), not to a side effect of a download. Pass a season to roll it.

    Imported inside the function rather than at module scope: `--check` must run without the model.
    """
    from src.models.export_frontend import export, export_live
    from src.models.train_model import (
        ALERT_LIST_LIVE, load_panel, write_alert_list, write_forecast,
    )

    panel = load_panel()                      # trims the unsettled tail -- the short-week refusal
    season = season or served_season(int(panel["Anio"].max()))
    _, path = write_alert_list(panel, season)
    print(f"OK  alert list -> {path.name}, season {season}")

    # The forecast is the only artifact here about a week that has not happened, and it is written
    # every run precisely because it expires every week: a stale forecast.parquet is a claim about
    # a week whose answer is already in. The alert list above is a finished season and does not
    # rot the same way.
    fc, fpath = write_forecast(panel)
    tgt = fc.groupby("horizon").first()
    print(f"OK  forecast -> {fpath.name}, origin {tgt['origin_year'].iloc[0]} "
          f"w{tgt['origin_week'].iloc[0]} -> "
          + ", ".join(f"h={h} w{r['week']} ({int(fc[fc['horizon'] == h]['alert'].sum())} alerts)"
                      for h, r in tgt.iterrows()))

    # The current season, for the weeks BEHIND the now-line on the live screen. Separate from the
    # served season above: rolling the explorer from a finished 2025 to a partial 2026 changes what
    # the product IS, and this does not do that -- it adds a second artifact for a second screen.
    current = int(panel["Anio"].max())
    _, live_list = write_alert_list(panel, current, path=ALERT_LIST_LIVE)
    print(f"OK  current-season alert list -> {live_list.name}, season {current}")
    export()
    return export_live()


def refresh(force=False, export=True):
    """Download, validate, install if it differs, re-export. Returns a summary.

    **It always downloads.** The obvious saving -- skip when CKAN's `last_modified` has not moved --
    was built and then measured false: on 2026-08-03 CKAN reported the release as published
    2026-07-29, the date of the file already on disk, and the download came back with **660 more
    rows**. DEIS revises the file in place without moving the timestamp, so `last_modified` cannot
    answer "is there anything new". Seventy megabytes a week is not worth a wrong answer, and the
    honest test is the content, which `validate` reads anyway.
    """
    remote = release()
    tmp = WEEKLY_PARQUET.with_suffix(".incoming")
    print(f"downloading  DEIS release published {remote['published']} "
          f"({(remote['size'] or 0) / 1e6:.0f} MB) ...")
    fetch(remote["url"], tmp)
    try:
        rows, newest = validate(tmp, WEEKLY_PARQUET)
    except (AssertionError, duckdb.Error):
        tmp.unlink(missing_ok=True)     # what is on disk is untouched and still servable
        raise

    # ponytail: row count plus newest week, not a checksum. A false "unchanged" costs one skipped
    # export of a file that looks identical; a false "changed" costs one redundant export. Reach
    # for a hash only if either ever costs more than that.
    if not force and WEEKLY_PARQUET.exists() and coverage(WEEKLY_PARQUET) == (rows, newest):
        tmp.unlink(missing_ok=True)
        print(f"unchanged  {rows:,} rows through week {newest[1]} of {newest[0]}, identical to "
              f"what is served. Nothing installed; pass --force to re-export anyway.")
        return {"downloaded": True, "changed": False, "rows": rows, **remote}

    install(tmp, WEEKLY_PARQUET)

    RELEASE.parent.mkdir(parents=True, exist_ok=True)
    RELEASE.write_text(json.dumps(
        {**remote, "fetched": date.today().isoformat(), "rows": rows, "newest_raw_week": newest},
        indent=2), encoding="utf-8")
    print(f"OK  {rows:,} rows, newest RAW week {newest[1]} of {newest[0]} -- the unsettled tail is "
          f"trimmed downstream, so the week actually served is older than this one.")

    return {"downloaded": True, "changed": True, "rows": rows, "newest_raw_week": newest,
            **remote, **({"export": str(rebuild())} if export else {})}


def demo(tmp=None):
    """Self-check for the only step that can lose data. No network, no model, synthetic parquets."""
    import tempfile

    import pandas as pd

    def parquet(path, weeks, year=2026, cause=TARGET_ORDEN_CAUSA):
        pd.DataFrame({"Anio": year, "SemanaEstadistica": list(weeks),
                      "OrdenCausa": cause, "NumTotal": 1}).to_parquet(path, index=False)
        return path

    with tempfile.TemporaryDirectory() as d:
        d = Path(tmp or d)
        served = parquet(d / "served.parquet", range(1, 21))
        assert coverage(served) == (20, (2026, 20))

        # DEIS keeps a week-53 bucket in every snapshot. Counting it pinned `newest` at 53 for
        # every file ever published, which silently disabled the backwards guard below.
        assert coverage(parquet(d / "wk53.parquet", [*range(1, 21), 53])) == (20, (2026, 20)), \
            "week 53 must be excluded here exactly as load_weekly_target excludes it"

        # The happy path: a week further on, more rows.
        assert validate(parquet(d / "newer.parquet", range(1, 22)), served) == (21, (2026, 21))
        # A first-ever refresh has nothing to compare against and must not block on that.
        assert validate(served, d / "absent.parquet") == (20, (2026, 20))

        for name, weeks, why in [
            ("older", range(1, 20), "a snapshot that ends earlier must be refused"),
            ("short", [1, 2, 20], "a truncated file must be refused"),
        ]:
            try:
                validate(parquet(d / f"{name}.parquet", weeks), served)
            except AssertionError:
                pass
            else:
                raise AssertionError(why)

        # Wrong cause section: the file parses, and reading it would train on hospitalizations.
        try:
            coverage(parquet(d / "wrong.parquet", range(1, 21), cause=33))
        except AssertionError:
            pass
        else:
            raise AssertionError("a file without the target cause must be refused")

        install(parquet(d / "incoming.parquet", range(1, 30)), served)
        assert coverage(served) == (29, (2026, 29)), "install did not replace the served file"
        assert (d / "served.parquet.bak").exists(), "install dropped the previous file"
        assert coverage(d / "served.parquet.bak")[0] == 20, "the backup is not the previous file"

    print("OK  refresh guards: backwards snapshot, truncated download and wrong cause all refused; "
          "the served file survives every refusal and the previous one is kept as .bak")


if __name__ == "__main__":
    if "--check" in sys.argv:
        demo()
    else:
        refresh(force="--force" in sys.argv)
