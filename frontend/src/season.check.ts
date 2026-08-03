/* `npm run check` — node's own type stripping and assert, no test framework.
   The one thing worth failing on: a gap in the scored weeks must break the series, and the verdict
   must not congratulate a facility that was never warned. */

import assert from "node:assert/strict";
import type { Facility } from "./data.ts";
import { axisWeeks, freshness, runs, seasonLength, summarize, verdict } from "./season.ts";

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

console.log("OK  season.ts: week-space runs, axis, summary, verdict and the AC-I9 stamp");
