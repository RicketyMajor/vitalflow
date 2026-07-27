# VitalFlow: Early Warning System for Respiratory Emergency-Room Saturation

> **Document status.** Rewritten 2026-07-27. The previous version described a 4-to-8-week forecasting
> system built on a Temporal Fusion Transformer over spatially clustered facilities, with air quality
> as the driving covariate. Each of those three commitments was tested and none survived
> (`notebooks/03b`, `03c`, `03d`, `03e`). This version describes what the data supports. Design
> rationale that is still valid is preserved; the reasoning behind each change is in
> `context/decisions/log.md`, newest first.

## 1. Problem Context

Chilean emergency rooms saturate every winter. Respiratory attentions roughly triple between the
summer trough and the July peak, and the response is largely reactive: staff are reassigned, beds
are opened and elective procedures are deferred once the waiting rooms are already full. The cost
lands on waiting times, staff burnout and quality of care.

The demand itself is not mysterious — it is the winter respiratory epidemic, and its broad shape is
known months ahead. What is not known is *this* year's departure from that shape: whether the wave
arrives early, how steep it is, and which week a given facility will exceed what it can absorb.

## 2. Justification

A hospital that knows next week will be heavy can call in relief staff, reschedule shifts, open
contingency beds and defer non-urgent procedures. Those are the levers that operate on a horizon of
days to a fortnight, and they are the levers this system serves.

Longer-lead decisions — hiring, budget reallocation, structural capacity — would need one to two
months of warning. **That warning is not obtainable from the available data, and Section 5b explains
in measured terms why.** Claiming otherwise would produce an alert list no better than a wall
calendar, which is precisely what the earlier framing was heading towards.

## 3. Problem Definition

Forecast the **weekly count of respiratory emergency attentions per health facility in Chile at a
1-to-2-week horizon**, and deliver it as a **ranked alert list**: for each facility, the weeks most
likely to exceed its own historical 90th percentile of demand.

The deliverable is the ranking, not the number. A hospital acts on "staff up for week 27", not on a
point estimate with a confidence interval.

## 4. Problem Type

Three chained problems, each matched to the structure that was actually measured in the data
(Section 5b):

1. **Univariate time-series forecasting** of the national respiratory anomaly — one series, weekly.
2. **Cross-sectional allocation** of that national forecast to 622 facilities, via each facility's
   own seasonal climatology and its loading on the national factor.
3. **Binary classification with class imbalance** — P(surge) per facility-week, ranked to fill a
   fixed alert budget. Surges are ~8% of facility-weeks.

Not a panel deep-learning problem. The reason is in Section 5b and Section 9.

## 5. Objectives

1. Forecast the national respiratory wave at 1–2 weeks, beating the seasonal climatology by a
   measurable margin on out-of-sample data, scored **within** each test season.
2. Convert that forecast into a per-facility alert list that beats climatology on **surge recall and
   precision at a fixed alert budget** — the metric an administrator actually consumes.
3. Serve it: an automated weekly pipeline from the DEIS open data release to a ranked alert list per
   facility, with an interface a hospital administrator can read without a data scientist present.
4. Keep the honest scope visible in the product itself. A system that says "two weeks" and delivers
   two weeks is worth more than one that promises two months and delivers noise.

## 5b. What Was Tested and Refuted

This section is the most load-bearing part of the document. Every entry is an out-of-sample
measurement, not an opinion, and each one closed a direction the project had been assuming.

| Hypothesis | Verdict | Evidence |
| :--- | :--- | :--- |
| Air pollution predicts respiratory ER demand | **Refuted.** Real but worth under 0.5 percentage points of R² once seasonality is removed | `03b` |
| A panel R² of 0.91 means the problem is nearly solved | **Refuted.** 60.1% of panel variance is facility identity, 20.5% is the calendar, 13.0% is the anomaly — the only part that is a forecasting problem | `03c` |
| Epidemic waves propagate between facilities, so neighbours give early warning | **Refuted.** Lead-lag correlation is symmetric to within ±0.006 at every distance from 25 to 400 km. The 100–400 km ring correlates as strongly as the 0–25 km ring: one synchronous national wave, no travelling front | `03d` |
| Some facilities are sentinels that ignite first | **Refuted.** Split-half reliability of peak-week earliness across seasons: +0.09 | `03d` |
| Cross-facility features improve the alert list | **Refuted.** They double R² on the anomaly at 8 weeks (0.077 → 0.147) and leave surge recall unchanged. A national index shifts every facility at once; it improves the average without re-ordering the ranking | `03d` |
| Laboratory virological surveillance leads ER demand | **Refuted.** Influenza positivity peaks against the ER anomaly of the *previous* week — a specimen exists because a patient already presented. Adding it to the forecast is negative at every horizon, including an oracle with no publication lag | `03e` |
| Paediatric demand leads elderly demand usefully | **Partially true, not usable.** The lead is real (asymmetry +0.11 to +0.14) but scored within season the resulting model is negative in all seven test seasons | `03e` |
| Forecast the season instead of the week | **Refuted on sample size.** Nine usable seasons; peak-week autocorrelation between consecutive seasons is −0.25 | `03e` |

**The horizon wall.** Within-season out-of-sample R² on the national anomaly, median over seven test
seasons, using the series' own history:

| horizon | 1 wk | 2 wk | 3 wk | 4 wk | 6 wk | 8 wk |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| median R² | **0.835** | **0.598** | 0.274 | −0.063 | −0.277 | −0.266 |

Three weeks, and sharp. No predictor tested moves it. This is the single measurement the project's
scope now rests on.

## 6. Methodology: The Machine Learning Life Cycle

| Phase | Mapping to VitalFlow | Status |
| :--- | :--- | :--- |
| **1. Data Engineering** | DEIS weekly ER Parquet; canonical loaders with the target definition, categorical normalisation and a COVID regime flag; WHO FluNet virological series | 🟢 Complete for the current scope |
| **2. Analysis** | Variance decomposition, horizon sweep, spatial lead-lag, exogenous indicator tests | 🟢 Complete — `03b` through `03e` |
| **3. Modeling** | National wave forecast → facility allocation → surge classifier, evaluated on recall/precision at a fixed alert budget | 🔴 Next |
| **4. Deployment & Serving** | Weekly batch job producing a ranked alert list; API and interface | 🔴 Not started |
| **5. Monitoring** | Score each week's alert list against what actually happened; retrain on schedule | 🔴 Not started |

Note that phase 2 is listed separately. It consumed four notebooks and eliminated five candidate
directions before a single model was trained, which is the reason the modelling phase is now a
week's work instead of a quarter's.

## 7. Technology Stack

**Modelling: scikit-learn.** `RidgeCV` for the national wave, `HistGradientBoostingClassifier` for
the surge probability. Both already installed. No new dependency, no GPU.

> **What was removed and why.** `torch` and `pytorch-forecasting` are not installed and are not
> planned. A Temporal Fusion Transformer needs a panel with cross-series structure to attend over;
> `03d` measured that structure and it is absent. The wave itself is ~500 weekly observations. The
> 12 GB VRAM constraint that shaped several earlier decisions no longer binds anything.

**Serving.** The model is small enough to run in seconds on CPU, and the input arrives in weekly
batches, so the original Redis + FastAPI + Node.js three-service architecture is heavier than the
problem. The lean version is a scheduled weekly job that writes the alert list, plus a small API and
a static frontend that reads it. The distributed design remains a legitimate choice if real-time
multi-user alerting becomes a goal; it should be a deliberate decision rather than an inherited one.

## 8. Data

### 8.1. Target variable

**Source:** `data/raw/Atenciones de Urgencia/Atenciones de urgencias de causas respiratorias por semana epidemiológica/at_urg_respiratorio_semanal.parquet` (DEIS / MINSAL).

**Definition:** `OrdenCausa = 3` — *TOTAL CAUSA SISTEMA RESPIRATORIO (J00-J98)*, weekly count per facility.

| Property | Value |
| :--- | :--- |
| Granularity | Epidemiological week × facility |
| Coverage | 2014 – week 29 of 2026 |
| Facilities | 632 |

The taxonomy is strictly hierarchical and was verified empirically: sub-causes `OrdenCausa` 4–9
(IRA Alta, Influenza, Neumonía, Bronquitis/bronquiolitis, Crisis obstructiva bronquial, Otra causa
respiratoria) sum to `OrdenCausa = 3` **exactly**, with zero drift across 56,072,767 events.

> ⚠ **Do not select causes by text matching.** `OrdenCausa = 33` is labelled
> *"- Causas sistema respiratorio (J00-J98)"* and is a **hospitalization** subtotal, not an ER
> attention. A `LIKE '%RESPIRATORIO%'` predicate captures it and silently inflates the target.
> Import from `src/features/build_features.py` instead of rewriting the query.

This dataset also carries the static attributes the model needs, with no join required:
`RegionGlosa`, `ComunaGlosa`, `ServicioSaludGlosa`, `TipoEstablecimiento`, `DependenciaAdministrativa`,
`NivelAtencion`, `TipoUrgencia`, `NivelComplejidad`, `Latitud`, `Longitud`.

**Alternative considered and rejected as primary:** the daily dataset
(`data/processed/urgencias_parquet/`, 817 facilities, 2017–2024) offers finer granularity but stops
18 months before the present, carries no facility metadata, and loses 83 facilities to a fragile
coordinate join. Weekly resolution matches how Chilean epidemiological surveillance already
operates, and reaches the current week.

### 8.2. Exogenous variables

| Source | What it provides | Coverage | Status |
| :--- | :--- | :--- | :--- |
| **WHO FluNet** | National weekly virological surveillance: specimens processed, influenza A/B, RSV, adenovirus, parainfluenza, metapneumovirus | Influenza 1997–; RSV and others 2015– | Downloaded and **tested — no predictive value** (`03e`). Loader: `load_virology()` |
| **SINCA (MMA)** | MP2.5 / MP10 daily concentrations, 199 stations | 2023 – 2025 | Processed; **tested — under 0.5 pp of R²** (`03b`) |
| **DMC yearbooks** | Monthly climatological variables, 165 canonical stations | 2005 – 2025 | Extracted, unused. Monthly resolution is too coarse for a weekly model |
| **CR2 Explorador Climático** | Alternative climate series, possibly weekly | — | Downloaded, never examined |
| **INE Censo 2024 / DPA** | Comunal geometries and administrative codes | 2024 | Downloaded, unused |
| **IGVUST** | Socio-territorial vulnerability index per comuna | — | Downloaded, unused. Static, so it can only explain between-facility variance — which climatology already absorbs |
| **DEIS REM20** | Hospitalisation process indicators | to 2026-06 | Downloaded, unused; candidate capacity proxy for defining saturation rather than demand |

> **A pattern worth naming.** Every exogenous source tested so far has failed for the same reason: it
> is either seasonal (and so redundant with the calendar), static (and so redundant with facility
> identity), or contemporaneous-to-lagging (and so redundant with the ER series itself). A candidate
> covariate is only interesting if it is none of those three. Test that before ingesting anything new.

> **Serving gap.** No exogenous source is required by the current design, which removes the
> deployment blocker the previous version of this document carried. The model needs the DEIS weekly
> release and nothing else.

### 8.3. Known data hazards

Established facts from the audits, not risks:

1. **COVID structural break.** ER attendance collapsed in 2020 (−65% vs 2019) and 2021 (−51%), then
   overshot in 2022. This is genuine demand collapse, not under-reporting: *more* facilities reported
   in 2020 than in 2019. Exclude both years, or carry an explicit regime indicator.
2. **Extreme skew and kurtosis.** Raw daily counts show skewness 6.35 and excess kurtosis 822; the
   1–4 age band reaches 112,140. A variance-stabilising transform is mandatory. The **cube root** was
   selected over `log1p` after benchmarking every zero-tolerant candidate.
3. **Exact accounting identity.** The five age bands sum to the total in 100% of rows, giving VIF = ∞.
   Model the total **or** the decomposition, never both.
4. **Unbalanced panel.** Facilities enter and leave the register; an unreported week is not a
   zero-demand week and must be masked, not imputed as zero.
5. **Week 53 is a partial-week bucket**, averaging ~36k national attentions against ~104k for a
   normal week. Dropped in the canonical loader.
6. **Dirty categorical metadata.** Whitespace and case variants fragment categories silently:
   `"Municipal"` vs `"Municipal "` (418 vs 13 facilities), and — found in `03d` —
   `"Región De Los Ríos"` vs `"Región De los Ríos"` (21 vs 6), which splits one region in two for any
   group-by. `normalize_category` collapses whitespace but deliberately not case; casefold before
   aggregating by region.
7. **Invalid coordinates.** `hospital_sinca_dmc_mapping.csv` contains a nearest-neighbour distance of
   3,509 km — impossible in Chile — and mojibake in 1,739 of 4,025 facility names
   (`MÃ©dico` → `Médico`). Both are handled in `src/data/make_dataset.py`.
8. **FluNet publication lag.** A week is published roughly two weeks after it ends. Any backtest
   using it must impose that delay or it reads data that did not exist yet.

## 9. Model Design

The architecture is dictated by the measured variance decomposition (`03c`): 60.1% between
facilities, 20.5% seasonal within facility, 13.0% anomaly. The first two components are free — a
facility identifier and a calendar produce them — so the model exists to forecast the third, and the
third is one national series (`03d`).

### 9.1. Stage 1 — the national wave

A single weekly series: the cross-facility mean of standardized facility anomalies. Forecast at
h = 1 and h = 2 from its own recent history (lags 1, 2, 4 and a four-week change), with `RidgeCV`
selecting the regularisation.

**Measured baseline to beat:** median within-season out-of-sample R² of 0.835 at one week and 0.598
at two, already achieved by this specification in `03e`. Any added complexity must beat that number
on the same protocol.

### 9.2. Stage 2 — allocation to facilities

Each facility's forecast is its own week-of-year climatology plus its loading on the national
anomaly:

```
demand_hat[i, w] = climatology[i, week_of_year(w)] + beta[i] * national_anomaly_hat[w]
```

A factor model, matching the variance split directly. `beta[i]` is estimated per facility on the
training years, shrunk toward the panel mean for facilities with short history.

### 9.3. Stage 3 — the alert list

A `HistGradientBoostingClassifier` emitting P(surge) per facility-week, where a surge is a week above
that facility's own historical 90th percentile. Features: the Stage 2 forecast, the facility's recent
anomalies, its climatology and seasonal position, static metadata, and the national forecast.

**Why a classifier rather than thresholding a point forecast.** `03d` produced a model with double
the R² and an identical alert list. Optimising a conditional mean and thresholding it afterwards
optimises the wrong thing: what matters is the *ranking* of facility-weeks by risk. A classifier
trained on the surge event optimises that ranking directly.

**Evaluation protocol — fixed alert budget.** Each facility alerts on its own top 10% of weeks,
about five per year. Every model spends the same alert budget, which is what makes recall and
precision comparable; a model that alerts more often would otherwise win on recall by shouting.
Scored with an expanding window, one test season at a time, never pooled across seasons — pooling
credits a model for predicting differences *between* seasons, which nearly produced a false positive
in `03e`.

**Benchmarks to beat** (surge recall at a fixed budget, h = 1, from `03d`):

| | test 2025 | test 2024 |
| :--- | ---: | ---: |
| climatology | 0.243 | 0.257 |
| best current model | 0.321 | 0.428 |

### 9.4. Explicitly excluded

| Rejected | Reason |
| :--- | :--- |
| Temporal Fusion Transformer | ~500 observations for the wave; no cross-facility structure to attend over (`03d`) |
| HDBSCAN catchment clustering | Premised on spatial propagation, which does not exist (`03d`) |
| Pollution and weather covariates | Under 0.5 pp of R² (`03b`); monthly climate data is too coarse |
| Virological surveillance features | Lagging, not leading (`03e`) |
| Season-ahead peak forecasting | Nine seasons, autocorrelation −0.25 (`03e`) |
| Horizons beyond three weeks | No predictor tested produces positive within-season skill (`03e`) |

## 10. Repository Structure

```text
vitalflow/
├── data/                           # local only, gitignored — see context/sources/index.md
│   ├── raw/                        # DEIS, SINCA, DMC, CR2, INE, IGVUST, WHO FluNet
│   ├── processed/                  # Parquet conversions, station mappings
│   └── external/
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 01b_csv_to_parquet_duckdb.ipynb      # CSV → Parquet via DuckDB
│   ├── 01c_sinca_python_scraper.ipynb       # Python rewrite of the original R scraper
│   ├── 02_feature_engineering.ipynb         # stale: predates the target correction
│   ├── 03_eda_comprehensive.ipynb           # statistical audit
│   ├── 03b_pollution_demand_hypothesis.ipynb  # is pollution the signal? no
│   ├── 03c_forecastability_and_horizon.ipynb  # what is forecastable, and when
│   ├── 03d_spatial_leadlag.ipynb              # do neighbours lead? no
│   ├── 03e_virology_and_horizon_wall.ipynb    # does the lab lead? no. where is the wall? 3 weeks
│   ├── 03_spatial_clustering_hdbscan.ipynb    # empty — spec superseded
│   └── 04_tft_model_baseline.ipynb            # empty — not the plan any more
├── src/
│   ├── data/make_dataset.py        # canonical target + virology loaders, self-check
│   ├── features/build_features.py  # weekly panel, geodesics, deseasonalization, self-check
│   └── models/{train,predict}_model.py   # empty stubs — Section 9 goes here
├── services/                       # scaffolded, empty
├── frontend/                       # scaffolded, empty
├── docs/vitalflow-project.md       # this file
├── context/                        # working memory: specs, decisions, handoffs (gitignored)
├── docker-compose.yml              # empty
├── requirements.txt
└── README.md
```

## 11. Immediate Next Steps

1. **Implement Stage 1** in `src/models/train_model.py`: the national wave forecast at h = 1 and 2,
   with the expanding-window backtest as its self-check. Target: reproduce R² 0.835 / 0.598.
2. **Implement Stages 2 and 3**, and score the alert list against the benchmarks in §9.3. If the
   classifier does not beat climatology on recall at a fixed budget, it does not ship — regardless of
   its R².
3. **Automate the weekly refresh** from the DEIS release, and produce the alert list as a file.
4. **Build the interface** on top of that file: per facility, the next two weeks' alert status and
   the seasonal context that justifies it.
5. **Only then** revisit covariates, against the filter in §8.2: not seasonal, not static, not
   contemporaneous.
