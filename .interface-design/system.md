# VitalFlow — interface system

Ported 2026-08-02 from `frontend/alert-interface-mockup.html`, the reference implementation.
**The direction is settled** in `context/specs/alert-interface.md` and is not reopened here; this
file records the values so they survive a session. Live tokens: `frontend/src/styles.css`.

## Direction and feel

**"La pizarra del turno"** — a hospital shift board, not a SaaS dashboard. Pale green-cold surfaces
under fluorescent light. Monospaced type for every datum, because an epidemiological week is a code,
not a word. One institutional ink, used only where there is an alert.

Every choice answers to a measurement (`context/decisions/log.md`):

| Constraint | Why | Where it bites |
| :--- | :--- | :--- |
| The **calm** screen is the primary screen | 94% of facility-weeks carry no alert; ~40% of facilities none all season | Calm gets the design effort; it is never an empty state |
| **No probability, ever** | Calibration measured and rejected 2026-07-29 | Only an ordinal rank within the facility's own season |
| **No third decimal** | Row-order sensitivity envelope, 2026-07-30 | Two significant figures on screen |
| **No triage colours** | Red/amber/green are clinically loaded in a Chilean ER | Calm carries no accent at all |
| Origin W−1, horizon **h=2** | 2026-07-28 / 07-29 | Both weeks named, the gap drawn |

## Tokens

Light is the default; dark is a selected set, not a flip. Both ship via `prefers-color-scheme`
plus `:root[data-theme]` overrides.

| Token | Light | Dark | Role |
| :--- | :--- | :--- | :--- |
| `--muro` | `#e9edea` | `#0f1412` | page wall |
| `--pizarra` | `#f7f9f7` | `#161d1a` | the board (card surface) |
| `--hueco` | `#dfe4e1` | `#1e2623` | inset wells; weeks that have not happened |
| `--borde` | `rgba(20,26,24,.11)` | `rgba(232,237,234,.10)` | card edge; also the *watched week* fill |
| `--borde-int` | `rgba(20,26,24,.07)` | `rgba(232,237,234,.06)` | internal dividers |
| `--tinta` | `#141a18` | `#e8edea` | primary text |
| `--rotulo` | `#56635e` | `#96a49d` | secondary text |
| `--tenue` | `#8b968f` | `#6d7a74` | metadata, labels, axes |
| `--alerta` | `#1f4a7a` | `#7fb0e6` | **the only accent.** MINSAL institutional blue |
| `--alerta-df` | `rgba(31,74,122,.12)` | `rgba(127,176,230,.16)` | alert wash (guides, diffuse marks) |
| `--campana` | `rgba(31,74,122,.075)` | `rgba(127,176,230,.10)` | Campaña de Invierno band, weeks 22–35 |

**Two fixes to the maquette's values, made 2026-08-02 when the ported code was looked at on screen.**
`--campana` was `.05 / .06` and the band was invisible in both modes — a legend key for something
nobody could see. Raised to `.075 / .10`, still well under `--alerta-df` so the accent keeps its
rank. And `.semana--campana::before` carried `z-index:-1`, which puts the wash *behind*
`.tablero`'s own background; it now paints over the cell, where at 7% it reads the same.

**Type.** `--mono` = `ui-monospace, "SF Mono", "Cascadia Mono", "Segoe UI Mono", Menlo, Consolas`;
`--prosa` = `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Mono for every datum, label
and code; prosa for sentences only. Body 15px/1.55.

**Spacing.** Base unit `--u: 4px`; every gap and pad is a multiple. Radii `--r-chico: 3px`,
`--r-medio: 6px`.

**Depth: borders only.** No shadows anywhere — a board is flat under fluorescent light. Separation
comes from 1px `--borde` / `--borde-int` and from space.

## Component patterns

- **`.tablero`** — the board. `--pizarra` on 1px `--borde`, 6px radius, `overflow:hidden`; sections
  stacked and divided by 1px `--borde-int`, never by shadow or gap.
- **`.estado`** — the focal block, one per screen, dominating by size and air. Label 11.5px mono
  uppercase `.14em` · headline **40px mono 600** (30px under 620px) · gloss ≤56ch. In the alert
  variant the label and headline take `--alerta`; nothing else on the screen does.
- **The verdict block carries no accent** (explorer only). On the live alert screen the ink marks
  the alert; on the retrospective screen the headline is a *verdict*, and painting "3 alzas ·
  ninguna avisada" in institutional blue would turn the ink into a quality signal it does not mean.
  Blue appears only where the model actually fired: ribbon cells, series columns, lane ticks.
- **`.horizonte`** — origin → target drawn, not described: `Semana N` · hairline segment with an end
  tick · `Semana N+2`. 12.5px mono, tabular-nums.
- **`.cinta`** (the signature) — one cell **per epidemiological week of the season**, `flex:1 1 0`,
  `min-width:6px`, 2px gaps, 26px tall, rising to **34px** when alerted or over the threshold.
  `--hueco` no data · `--borde` watched · `--tinta` over the facility's own p90 · `--alerta`
  alerted · both at once = blue cell with an 8px ink cap · `--campana` band over weeks 22–35. Axis
  at 1 / 13 / 26 / 39 / last. It is what makes silence read as *accumulated surveillance* rather
  than as absence.
  **Index by week number, never by array position** — five facilities are scored on non-contiguous
  weeks (105107 has 37 scattered between week 1 and week 49), and packing them together draws a
  short season as a full one.
- **`.hechos`** — `repeat(auto-fit, minmax(190px,1fr))`, cells divided by a left border (a top
  border under 620px). `dt` 11px mono uppercase `.1em` `--tenue` · `dd` 19px mono 600 tabular ·
  `small` in prosa 12.5px `--rotulo`.
- **`.vigilancia`** — the trust footer, on `--muro` so it reads as outside the board: weeks watched,
  DEIS snapshot, and a 6px `--rotulo` pulse dot. It is the audit's answer to a silent season.
- **`.nota`** — the annotation layer, 11.5px mono uppercase `--tenue`. It is *about* the product and
  is never part of it.

## Chart encoding — the weekly series (added 2026-08-02, AC-E4)

One series, one accent, and the disagreement has to read without a legend lookup. Colour cannot
carry it — there is only one ink — so **geometry does**:

- **The x axis is the week number, 1..52**, identical for every facility, so a gap in the scored
  weeks breaks the line instead of being interpolated across. `season.ts` owns that arithmetic and
  `npm run check` fails if it regresses.
- **Attentions**: 2px `--rotulo` line, round join/cap. The series is context; it is not the accent.
- **The facility's own p90**: 1px solid `--tenue` rule with the value labelled at the right end.
  Solid, never dashed.
- **Observed surge**: a filled `--tinta` dot with a 2px `--pizarra` ring, drawn only on weeks above
  the rule. *A surge is legible as geometry* — the point sits above the line — so the dot confirms
  rather than encodes.
- **Alerted week (h=2)**: a full-height `--alerta-df` column behind the plot plus a solid `--alerta`
  tick in a lane below the axis. Blue means "the model said something".

That gives one sentence a reader keeps: **blue = we warned · above the rule = it happened.**
Agreement is a dot standing on a blue column; a false alarm is a blue column with nothing above the
rule; a **miss** is a dot above the rule with no blue under it. Facility 129103 is the test case —
surges in weeks 19/21/33, its only alert in week 50 — and it must be readable at a glance.

No chart library, no legend box (one series), no value on every point: the hover readout carries the
rest. Hit rects span the full plot height, one per week.
