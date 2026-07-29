# VitalFlow: Early Warning System for Respiratory Demand Surges in Chilean Hospital Emergency Rooms

VitalFlow forecasts weekly respiratory emergency-room demand for each hospital emergency department in
Chile at a **1-to-2-week horizon**, and delivers it as a ranked alert list: the weeks each facility is
most likely to exceed **its own historical 90th percentile** of demand.

**It forecasts demand, not saturation.** The distinction is deliberate and was earned: saturation is
demand against capacity, and no capacity measure exists in the open data for most Chilean emergency
facilities. What is measured here is the numerator. The target survived three separate tests for
operational contamination — boarded patients generate no second attention, walkouts *are* counted as
NSP/Fuga, and the cause sections reconcile to the total with zero residual — so it is a clean measure
of demand pressure. See `context/decisions/log.md`, 2026-07-29.

**Who it is for.** The alert goes to the shift coordinator or *Jefe de Servicio de Urgencia* of a
hospital emergency department, and serves three levers that all operate at 48–72 hours: activating the
bed contingency plan, reassigning internal functions, and authorising reinforcement shifts against the
winter-campaign budget. Ambulatory units (SAPU/SAR/SUR) are **not** alert destinations — their
staffing is fixed and an alert there has no lever to pull — but they remain in the panel as training
data.

The horizon is short on purpose: it is the horizon the data supports, and §5b of
[`docs/vitalflow-project.md`](docs/vitalflow-project.md) documents in measured terms how that was
established. Base shift rostering is *not* among the levers served — the monthly roster closes on the
20th–25th of the preceding month, which needs 4–7 weeks of notice against a measured 3-week skill wall.

## Core Objectives

1. Forecast the national respiratory wave at 1–2 weeks, beating the seasonal climatology out of
   sample, scored **within** each test season.
2. Convert it into a per-facility alert list that beats climatology on **surge recall and precision
   at a fixed alert budget** — the metric an administrator actually consumes, rather than R².
3. Automate the weekly refresh from the DEIS open-data release and put a readable interface on top.

Scored on hospital emergency departments, which is the population the alert can reach.

## What the data says

Four analysis notebooks (`03b`–`03e`) measured the problem before any model was trained, and
eliminated most of the original plan:

| Question | Answer |
| :--- | :--- |
| Does air pollution predict respiratory ER demand? | Under 0.5 pp of R² once seasonality is removed |
| Is a panel R² of 0.91 a solved problem? | No — 60% is facility identity, 20% is the calendar, 13% is the anomaly |
| Do epidemic waves propagate between facilities? | No — one synchronous national wave, symmetric lead-lag at every distance |
| Does laboratory virological surveillance lead demand? | No — it lags. A specimen exists because a patient already presented |
| How far ahead is the series forecastable? | **Three weeks.** Within-season R² 0.84 / 0.60 / 0.27 at 1 / 2 / 3 weeks, negative beyond |

## Architecture

The measurements dictate a small model, not a large one:

1. **National wave** — one weekly series, `RidgeCV` on its own recent history.
2. **Allocation** — each facility's climatology plus its loading on the national anomaly (a factor
   model, matching the measured variance split).
3. **Alert list** — `HistGradientBoostingClassifier` emitting P(surge) per facility-week, ranked to
   fill a fixed alert budget.

**Stack:** DuckDB + Parquet for data, scikit-learn for modelling, a weekly batch job for serving.
No GPU. A Temporal Fusion Transformer and HDBSCAN clustering were the original plan and were dropped
once the structure they assumed was measured and found absent — see `context/decisions/log.md`.

## Project Structure

* `data/` — raw, processed and external datasets (local only, gitignored).
* `notebooks/` — exploration, the statistical audit, and the four analyses that set the scope.
* `src/` — canonical loaders (`make_dataset.py`, `build_features.py`) and models. Each module runs a
  self-check when executed directly.
* `services/`, `frontend/` — scaffolded, not yet implemented.
* `docs/vitalflow-project.md` — the full project definition: problem, data, hazards, model design.
* `context/` — working memory: specs, decision log, session handoffs.

## Getting Started

```bash
python -m venv venv && venv/Scripts/activate     # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python src/data/make_dataset.py                  # self-check on the target taxonomy and virology
python src/features/build_features.py            # self-check on the weekly panel
```

The datasets are not distributed with the repository; `context/sources/index.md` lists every source,
its path and how to refresh it.
