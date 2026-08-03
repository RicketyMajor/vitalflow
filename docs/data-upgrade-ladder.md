# The data upgrade ladder

VitalFlow is built end to end from **publicly available Chilean data**. Every number it reports can
be reproduced by a stranger with a browser, a laptop and no institutional access. That is a
deliberate constraint, and this document is the argument for why it makes the project more useful to
a partner rather than less.

**The pitch, stated so it can be checked:** if the model performs on coarse public data, the same
method on the finer data a hospital or a municipality already holds should perform better. This
document says *how much better, on which quantity, and for which upgrades* — and, equally, which
upgrades this project has already measured to be worthless.

A ladder that only promises is a wishlist. The refutations in §3 are what make §2 worth reading.

---

## 1. What the public data actually is, and what it is not

**It is not stale.** The primary target — DEIS weekly respiratory emergency attentions — is published
weekly through CKAN with zero lag and back-revised for months. The snapshot this project was built on
(2026-07-29) carries data through **2026 week 29**. Anyone claiming this project runs on old numbers
should open the CKAN endpoint in `context/sources/index.md` and check.

**The limitation is resolution.** Specifically:

| The public file gives | A partner's internal system holds |
| :--- | :--- |
| One row per facility per **epidemiological week** | One row per **patient encounter**, timestamped |
| Five age bands (`<1`, `1–4`, `5–14`, `15–64`, `65+`) | Age, and everything else on the DAU |
| A **count** of attentions | The count, plus **triage category**, waiting time, destination |
| Monthly bed occupancy (REM20), hospitals only | A **live bed census**, all units |
| A week that is 19.1% complete on the day it closes | The facility's own encounters, complete **today** |

Everything in §2 follows from that table.

---

## 2. The ladder — what each upgrade unlocks

Ordered by measured value, not by how impressive it sounds.

### A. The facility's own live encounter feed → **recovers a horizon the public product cannot serve**

**This is the largest single gain available, and it has nothing to do with the model.**

A DEIS week is **19.1% complete the day it closes** and 97.8% settled at seven days. A deployment
reading the public file must therefore take its origin at W−1 and forecast at **h=2**. Backtests that
read final values are measuring a horizon deployment does not have.

The project measured both horizons on identical rows:

| | h=1 (measured, not servable publicly) | h=2 (what the public product serves) |
| :--- | :--- | :--- |
| Onset recall vs the seasonal calendar | 0.221 vs 0.137 | +0.00 / +0.09 / +0.03 across three seasons |
| Within-season out-of-sample R² on the national anomaly | **0.772** | 0.450 |
| Margin over climatology, sealed 2026 holdout | 4.20× | 2.69× |

**A partner with its own encounter feed does not have the settling problem for its own facility.**
Its week is complete when the week is over. That moves the origin to W−0 and hands back h=1 —
where the margin over the seasonal calendar is several times larger. **No retraining is required to
collect this; it is a change of input latency.**

### B. Triage category → **the target stops being a pure count**

The project's title says saturation; the target measures a **demand percentile** and has never held a
capacity denominator. Triage category (REM A08 section B, "categorización") is collected at every
Chilean emergency unit and is not in the public per-facility series. With it, a surge can be defined
on **acuity-weighted demand** rather than on headcount — which is the difference between "many people
came" and "many people who needed a resuscitation box came".

**Expected gain: unmeasured, and stated as unmeasured.** This is the one item on the ladder the
project has no prior for, because the variable has never been in reach.

### C. A live bed census → **turns a demand forecast into a strain forecast**

REM20 is monthly and covers hospitals only. Against it, the target validated: a month containing a
p90 respiratory week sits **+0.060 SD** (2022–2026) above the facility's own occupancy norm for that
month of year, and the responding wards are **paediatric** (adult wards are a precise null). The
effect is *small*, and the monthly figure is a **lower bound** on the weekly one — converting between
them is an assumption, not a result.

**A daily census removes the coarsening.** The measurement that currently needs a whole month to
resolve one surge week could be made on the week itself.

### D. Boarding and walkout timestamps → **a direct strain outcome instead of a proxy**

`IdCausa` 27/28 ("pacientes en espera de hospitalización") exist in the public schema and are
**identically zero for all 358 facilities** — the field is defined and not populated. Walkouts are
recoverable indirectly as `TOTAL DEMANDA − TOTAL ATENCIONES`, and that was tested
(`specs/abandonment-construct-validity.md`): the pre-registered rate contrast **did not pass**, and
the audit showed the count rises at hospitals (**+0.06**, CI [+0.008, +0.122]) but not at ambulatory
facilities. **Exploratory, never pre-registered, and with no era replication possible** — the field
does not exist before 2020.

**A partner with real boarding times could pre-register that test properly.** This project cannot.

### E. Age at encounter → **the paediatric variant, honestly**

The strain the target predicts is paediatric; the target itself is all-ages. The public file's five
age bands already permit a coarse paediatric target, and the bands are in `load_weekly_target`. Exact
age refines it. **This is deliberately unbuilt** — it is easy, which is exactly why building it
speculatively would be wrong.

### F. Roster and contingency-budget data → **lets the alert be costed**

The product's riskiest assumption is unmeasurable with any amount of demand data: *is "2nd of 31"
actionable to a shift coordinator, or is it inert?* A partner's rostering and contingency-spend
records would let an alert be scored against what it actually cost and saved.

---

## 3. What more data will **not** fix

Every item here was measured and refuted inside this project. A partner should not be sold any of
them, and a reviewer should be able to see that we did not try.

| Upgrade someone will propose | Why it does not help | Where it was measured |
| :--- | :--- | :--- |
| **A longer forecast horizon** (4–8 weeks) | The wall is at **three weeks** and is a property of the signal, not of the model. Median within-season out-of-sample R² is 0.274 at h=3 and **negative from h=4**. No predictor tested moves it. | `03e`, and `overview.md` "Scope settled 2026-07-27" |
| **Air quality / pollution covariates** | Real but worth **under 0.5 pp of R²**. Four falsification checks, out-of-sample. | `03b` |
| **Virological surveillance as a leading indicator** | WHO FluNet **lags** the demand series rather than leading it. Kept on disk; ruling it back in should require new evidence. | `03e` |
| **Neighbouring-facility / spatial features** | Anomalies are **nationally synchronous, not spatially propagating** — symmetric at every distance, no sentinel facilities. This killed the clustering and the pooled model. | `03d` |
| **A bigger model class** (deep learning, transformers) | An ablation collapsed a three-stage design to **one classifier on six features**; dropping every national feature costs under 0.01 recall. The horizon wall closes the rest. | `train_model.py`, `specs/model-headroom.md` |
| **Calibrated probabilities** | Measured and **rejected — it makes the gap worse** (0.058 → 0.210 in 2024). The base rate moves 7.7% → 13.3% between seasons and that *is* the forecast target. The product shows a rank, never a percentage. | log 2026-07-29 |
| **More facilities** | 446 of 632 are ambulatory with no inpatient beds, where an alert has **no operational lever**. They stay as training rows deliberately. | log 2026-07-29 (physician scoping) |

---

## 4. What no data upgrade can supply

**Nobody it is for has read it.** The interface has had zero conversations with a Jefe de Urgencia.
Whether an ordinal ranking is actionable or inert is not a measurement question, and a finer dataset
does not answer it. It is recorded as an absence, not as a gap that more data closes.

---

## 5. If you are evaluating this project

Read in this order:

1. `README.md` — what it does and how to run it.
2. `PRODUCT.md` — who it is for, what it refuses to claim, and the absences it will not fabricate.
3. `#/evidencia` in the running frontend — every pre-registered prediction beside its outcome,
   including the four that missed their range and the one claim that was withdrawn.
4. This file — what would change with your data.

**The single number to judge it on:** at h=2, the horizon a public-data deployment can actually
serve, the margin over a facility × week seasonal calendar on **new** surges is **+0.00 / +0.09 /
+0.03** across three seasons. Not the widely quoted 0.221 vs 0.137 — that is h=1, and §2.A is the
argument for how a partner gets h=1 back.
