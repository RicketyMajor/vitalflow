# VitalFlow: Early Warning System for Respiratory ER Saturation

VitalFlow forecasts weekly respiratory emergency-room demand for each health facility in Chile at a
**1-to-2-week horizon**, and delivers it as a ranked alert list: for every facility, the weeks most
likely to exceed its own historical 90th percentile of demand. The lever it serves is operational —
shift rescheduling, relief staff, contingency beds.

The horizon is short on purpose. It is the horizon the data supports, and Section §5b of
[`docs/vitalflow-project.md`](docs/vitalflow-project.md) documents in measured terms how that was
established.

## Core Objectives

1. Forecast the national respiratory wave at 1–2 weeks, beating the seasonal climatology out of
   sample, scored **within** each test season.
2. Convert it into a per-facility alert list that beats climatology on **surge recall and precision
   at a fixed alert budget** — the metric an administrator actually consumes, rather than R².
3. Automate the weekly refresh from the DEIS open-data release and put a readable interface on top.

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
