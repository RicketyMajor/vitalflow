/* `npm run check` — node's own type stripping and assert, no test framework.
   The one thing worth failing on: a gap in the scored weeks must break the series, and the verdict
   must not congratulate a facility that was never warned. */

import assert from "node:assert/strict";
import type { Claim, Facility, Live } from "./data.ts";
import {
  axisWeeks, claimOf, freshness, liveState, liveVerdict, ordinal, runs, seasonLength, summarize,
  verdict,
} from "./season.ts";

// 105107's real shape: 37 scored weeks scattered between week 1 and week 49.
const sparse = [1, 2, 3, 20, 21, 49];
assert.equal(seasonLength(sparse), 52, "a short season still spans 52 weeks");
assert.equal(seasonLength([...sparse, 53]), 53, "a week-53 year widens the season");

assert.deepEqual(
  runs(sparse, [10, 20, 30, 40, 50, 60], 52),
  [[1, 2, 3], [20, 21]],
  "gaps break the line, and a lone week (49) starts no segment",
);
assert.deepEqual(
  runs([1, 2, 3], [10, null, 30], 52), [],
  "a missing observation breaks the line the same way a missing week does",
);
assert.deepEqual(runs([1, 2, 3], [10, 20, 30], 52), [[1, 2, 3]], "contiguous weeks are one run");

assert.deepEqual(axisWeeks(52), [1, 13, 26, 39, 52]);
assert.deepEqual(axisWeeks(39), [1, 13, 26, 39], "the last week is never duplicated");

const facility = (weeks: number[], attentions: (number | null)[],
                  surge: number[], alert: number[]): Facility => ({
  code: "x", name: null, comuna: null, region: null, type: null, complexity: null,
  season: 2025, retrospective: true, p90: 100, weeks, attentions, surge, onset: surge.map(() => 0),
  h1: { alert, rank: alert.map(() => 1) }, h2: { alert, rank: alert.map(() => 1) },
});

// 129103: surges in weeks 19/21/33, its only alert in week 50. Nothing was caught.
const missed = summarize(facility([19, 21, 33, 50], [200, 210, 269, 157], [1, 1, 1, 0], [0, 0, 0, 1]));
assert.equal(missed.surges, 3);
assert.equal(missed.alerts, 1);
assert.equal(missed.caught, 0, "an alert months after the season catches nothing");
assert.match(verdict(missed)[0], /ninguna avisada/, "a total miss must say so in the headline");

const calm = summarize(facility([1, 2], [10, 20], [0, 0], [0, 0]));
assert.equal(verdict(calm)[0], "Temporada en calma");

const hit = summarize(facility([1, 2], [200, 20], [1, 0], [1, 0]));
assert.equal(hit.caught, 1);
assert.match(verdict(hit)[0], /^1 de 1 alzas avisadas/);

// The peak is a row index into the facility's own arrays, not a week number.
assert.equal(summarize(facility([5, 9], [10, 99], [0, 0], [0, 0])).peak, 1);

// AC-I9: the stamp has to age. The failure that matters is the silent one — a job that stopped
// weeks ago still reading as current, which is a calm screen the reader cannot distinguish from
// a dead pipeline.
const day = (n: number) => new Date(Date.parse("2026-08-03T00:00:00") + n * 86_400_000);
assert.deepEqual(freshness("2026-08-03", day(0)), { dias: 0, viejo: false }, "today is fresh");
assert.deepEqual(freshness("2026-08-03", day(8)), { dias: 8, viejo: false }, "one weekly cycle");
assert.deepEqual(freshness("2026-08-03", day(9)), { dias: 9, viejo: true },
  "a missed refresh must be visible on the ninth day, not merely dated");
assert.deepEqual(freshness("2026-08-03", day(-2)), { dias: 0, viejo: false },
  "a stamp in the future is a clock disagreement, never negative age");

// ---- the live screen ------------------------------------------------------------------------
const live = (forecast: Claim[], stamp = "2026-08-04"): Live => ({
  ...facility([28, 29], [100, 110], [0, 0], [0, 0]),
  retrospective: false, origin: [2026, 29], stamp, forecast,
});
const aviso: Claim = { horizon: 2, week: 31, alert: 1, rank: 2, of: 31 };
const calmo: Claim = { horizon: 2, week: 31, alert: 0, rank: 19, of: 31 };
const hoy = new Date("2026-08-04T00:00:00");

assert.equal(liveState(live([aviso]), hoy), "aviso");
assert.equal(liveState(live([calmo]), hoy), "calma");
assert.equal(liveState(live([]), hoy), "sin-dato");
// Staleness outranks the alert. A three-week-old "alza probable" names a week already past.
assert.equal(liveState(live([aviso], "2026-07-01"), hoy), "vencido",
  "an expired forecast must not be presented as a current alert");
// `sin dato` must not be dressed as calm — the word would claim a week nobody observed was quiet.
assert.doesNotMatch(liveVerdict(live([]), "sin-dato", null)[0], /calma/i,
  "a facility with no forecast must not read as a calm season");
assert.equal(claimOf(live([{ ...aviso, horizon: 1, week: 30 }, aviso]))!.week, 31,
  "only h=2 reaches the screen");
assert.equal(ordinal(2), "2ª");

// AC-I8 case (a): a facility with no scored week at all. It reaches the browser as empty arrays,
// so every consumer of them has to survive it — `seasonLength([])` is the one that would throw.
const vacio: Live = { ...live([]), weeks: [], attentions: [], surge: [], onset: [],
                      h1: { alert: [], rank: [] }, h2: { alert: [], rank: [] } };
assert.equal(seasonLength(vacio.weeks), 52, "an empty season still spans 52 weeks");
assert.equal(summarize(vacio).watched, 0);
assert.equal(liveState(vacio, hoy), "sin-dato");

console.log("OK  season.ts: week-space runs, axis, summary, verdict, the AC-I9 stamp and the " +
            "four live states");
