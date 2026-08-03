# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**The Jefe de Urgencia / coordinador de turno at a Chilean hospital emergency department (UEH).**
Scoped by a physician on 2026-07-29 and narrowed again by an audit on 2026-07-30. They read the
alert at a nurses' station, between other things, at arm's length, and they have exactly three
levers that all run at 48–72 h: activate the bed contingency plan, reassign internal functions,
authorise mirror shifts against the winter-campaign budget. **Base staffing is not a lever** — the
monthly roster closes on the 20th–25th of the preceding month, so it needs 4–7 weeks of notice
against a horizon of 2.

Explicitly **not** the users: a clinician at the bedside, a MINSAL analyst, the general public. At a
SAPU/SAR (ambulatory unit) an alert has zero consequence, which is why 446 facilities carrying 73.7%
of respiratory attentions are training rows and not alert recipients.

**A second audience exists for the evidence surface only** (confirmed 2026-08-02): someone auditing
the method — a reviewer, a committee, MINSAL. That surface is layered so both read the same page at
two depths. It does not change who the product is for.

## Product Purpose

Forecast weekly respiratory emergency demand for each of the 180 Chilean hospital emergency
departments, one to two weeks ahead, and deliver it as a ranked alert list: the weeks each facility
is most likely to exceed **its own** historical 90th percentile. Success is a coordinator activating
a contingency plan 48–72 h before a week that turns out to be heavy, and *not* being asked to act in
the weeks that turn out normal.

## Positioning

**It forecasts demand, not saturation**, and it says so — the data holds no capacity denominator.
The comparison a neighbouring product cannot truthfully copy is the one this project actually ran:
its baseline is not "no model", it is the **seasonal calendar** (a facility × week climatology) and
a **zero-parameter persistence rule**, and it reports the horizon it can actually serve rather than
the one that scores better.

## Operating Context

- **Data:** DEIS weekly emergency attentions, 2014–2026, `IdCausa = 2` (respiratory). A DEIS week is
  ~19% complete the day it closes and 97.8% settled at 7 days, so **serving origin is W−1 and the
  operational horizon is h=2**. The series is back-revised: re-running a measurement a month later is
  a different measurement, not a replication.
- **Delivery:** a static, read-only web artifact over exported JSON. No backend, no API, no database
  — that design was considered and deleted as heavier than a CPU model refreshed weekly.
- **Calendar:** the declared Campaña de Invierno spans epidemiological weeks 22–35 and is what makes
  a mirror shift payable. The monthly roster closes on the 20th–25th of the preceding month.

## Capabilities and Constraints

- **180 hospital ERs, one season per export** (currently 2025); a multi-season export needs the
  alert list regenerated per year.
- **`score` is a ranking, not a probability.** Calibration was measured and rejected on 2026-07-29 —
  the base rate is the season severity the model exists to forecast. **No probability or percentage
  may appear anywhere in the product**, only an ordinal within the facility's own season, and no
  number is shown to three decimals.
- **The fit is reproducible but sensitive.** Permuting the input row order moves 2026 h=1 lift across
  7.94–8.31. **Two significant figures, never three.**
- **94% of facility-weeks carry no alert** and ~40% of facilities receive none across a whole season;
  for most of them that silence is correct. The calm state is the product's primary state.
- **Undecided, and not to be invented:** whether the product should forecast *paediatric* respiratory
  demand (the target is all-ages; the strain it predicts is paediatric); what `IdCausa = 34` ("TOTAL
  DEMANDA") is. Both are open questions for a physician.

## Brand Commitments

- **Name:** VitalFlow. **Language:** every user-facing surface is Spanish (Chile); code, comments and
  documentation are English.
- **Binding visual constraint, decided 2026-07-30 and explicitly not reopened:** "la pizarra del
  turno" — one institutional ink (MINSAL blue) used only where the model fired, **triage colours
  (red/amber/green) banned** because they carry a specific clinical meaning in that room, monospaced
  type for every datum. Recorded with its tokens in `.interface-design/system.md`.

## Evidence on Hand

Everything below is measured and reproducible from `src/models/train_model.py`. **None of it may be
rounded up, and the horizon must be named every time it is quoted.**

- **Sealed holdout, season 2026, pre-registered before the data was touched, run once.** All four
  acceptance criteria met: lift 5.19 vs climatology 1.92 at h=2 — **margin 2.69×** against a 2× floor.
- **Aggregate, h=1, 180 hospital ERs:** recall/precision 0.500/0.457 (2026), 0.464/0.498 (2025),
  0.403/0.686 (2024). Margins over climatology 4.20× / 3.32× / 2.26×.
- **The qualification that matters more than any of it:** 52–64% of those surge weeks are
  *continuation*, which needs no model. On onset (new surges) at matched spend, **h=2 — the horizon
  that deploys — the margin over the seasonal calendar is +0.00 (2024, an exact tie), +0.09 (2025),
  +0.03 (2026)**. The widely quoted 0.221 vs 0.137 is h=1.
- **Construct validity, pre-registered and then adversarially audited:** a month containing a week
  above the facility's own p90 sits **+0.060 SD (2022–2026) / +0.092 SD (2015–2019)** above that
  facility's own bed-occupancy norm for that month, negative-control wards flat. **The responding
  wards are paediatric; adult wards are a precise null** — replicated exploratory, never
  pre-registered, and it must be labelled so every time.
- **Absences future work must not fabricate:** no capacity denominator for the 446 ambulatory
  facilities (73.7% of volume) — formally untestable, not merely untested; no weekly percentage-point
  strain figure (the measurement is monthly and converting it is an assumption); no clinical outcome
  data; **no user research** — the interface has had zero conversations with a Jefe de Urgencia.

## Product Principles

1. **Name the horizon on every figure.** h=1 is a measurement; h=2 is the product.
2. **Silence is the product's normal state and gets the design effort** — rendered as accumulated
   surveillance, never as an empty state or an apology.
3. **The constraint goes in the data, not in the component.** "No probability anywhere" survives a
   redesign when the number is absent from the file and dies when it depends on discipline.
4. **Show the model being wrong.** A viewer that cannot display a surge nobody was warned about is
   not an honest viewer.
5. **Compare only at matched spend, and against a real baseline** — the seasonal calendar and
   persistence, never "no model".

## Accessibility & Inclusion

Read at arm's length at a nurses' station under fluorescent light, on whatever screen is there.
Colour is never the only channel: the one accent is always accompanied by position or shape, and no
information depends on distinguishing hues. Both light and dark are first-class, each with its own
selected values.
