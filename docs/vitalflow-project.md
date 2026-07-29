# VitalFlow: Early Warning System for Respiratory Demand Surges in Chilean Hospital Emergency Rooms

> **Renamed 2026-07-29, and the rename is a finding.** This document was titled *"…for Respiratory
> Emergency-Room Saturation"* for its whole life. Saturation is demand measured against capacity, and
> no capacity variable ever entered the model — none exists in the open data for the ambulatory
> facilities carrying 73.7% of respiratory volume. What is forecast is **anomalously high demand
> relative to each facility's own history**: weeks above its own 90th percentile. The target was then
> tested three ways for operational contamination and survived all three (`context/decisions/log.md`,
> 2026-07-29), so "demand" is not a hedge — it is the measured claim. "Hospital" is in the title
> because that is the only population the alert can reach.

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

> ⚠ **Weakened 2026-07-29 by clinical input** (Hospital Claudio Vicuña, single source). Allocation
> inside a Chilean ER is governed by **ESI five-level triage in real time**, not by advance
> planning. The alert is therefore closer to triage support than to an anticipatory scheduling
> signal, and the anticipatory levers listed above are a weaker justification than this section
> assumes — they may also belong to hospital management rather than to the ER floor. This settled
> the budget-rule question in favour of the national cut (§9.3) and it needs a second facility
> before anything rests on it.
>
> **Resolved 2026-07-29 by a second physician answer, and it strikes half of this section.** The
> rostering question above was asked and answered with a calendar: the *rol de turnos* closes between
> the **20th and the 25th of the preceding month**, signed and contractually committed under the
> Estatuto Administrativo (Ley 18.834) and the Leyes Médicas (Ley 19.664 / 15.076). Moving *base*
> staffing for a target week therefore needs **4 to 7 weeks** of notice, against a measured horizon
> wall of **3** (§5b). **The calendars are disjoint: "call in relief staff" and "reschedule shifts"
> are struck as levers, permanently and for a structural reason no model repairs.**
>
> **What this section may claim instead**, all of it confirmed available at 48–72 h and therefore
> comfortably inside h=2: activating the **bed contingency plan** (moving boarded patients to
> peripheral wards to free gurneys), **reassigning internal functions** (pulling the physician on
> *policlínico de choque* to reinforce the C3 box), and **authorising mirror shifts** against the
> contingency budget at +25/50% overtime. The recipient is the **Enfermero Coordinador de Turno /
> Jefe de Servicio de Urgencia** — not the physician on the floor, and not a SAPU, where an alert has
> zero operational consequence. See `context/decisions/log.md`, the two 2026-07-29 entries.

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

> **Corrected 2026-07-27 on implementation.** These figures come from `03e`, which fitted the
> facility climatology and scale over every year *including the test season* — and the anomaly those
> two quantities define is the target. Refitted per test season on earlier years only, the wall sits
> at **0.772 (h=1) and 0.450 (h=2)**. The shape of the wall and the conclusion drawn from it are
> unchanged; the levels are about 6 and 15 points lower. See §9.1.

## 6. Methodology: The Machine Learning Life Cycle

| Phase | Mapping to VitalFlow | Status |
| :--- | :--- | :--- |
| **1. Data Engineering** | DEIS weekly ER Parquet; canonical loaders with the target definition, categorical normalisation and a COVID regime flag; WHO FluNet virological series | 🟢 Complete for the current scope |
| **2. Analysis** | Variance decomposition, horizon sweep, spatial lead-lag, exogenous indicator tests | 🟢 Complete — `03b` through `03e` |
| **3. Modeling** | Three stages built and measured, then collapsed by ablation to one classifier on six facility features; evaluated on recall/precision at a fixed alert budget | 🟢 Complete — §9, AC2 met |
| **4. Deployment & Serving** | Alert list written to Parquet (§9.1); weekly refresh job and interface still to build | 🟡 Started |
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

> **Rewritten 2026-07-27 after implementation.** This section described a three-stage architecture —
> national wave → factor allocation → classifier. All three were built, measured, and scored
> (`src/models/train_model.py`). An ablation then showed the first two contribute under 0.01 recall
> to the alert list. What ships is §9.1; §9.2 records the three-stage measurement and why it was
> collapsed. Numbers below come from running the module, not from a notebook.

### 9.1. What ships

One `HistGradientBoostingClassifier` on P(surge) per facility-week, over **six features**:

| feature | meaning |
| :--- | :--- |
| `z`, `z_l1`, `z_l2` | the facility's standardized demand anomaly now and one and two weeks back |
| `z_d4` | its four-week change |
| `clim_z` | its seasonal position at the target week — where in its own year the week sits |
| `week` | week of year |

A facility-week is alerted when its P(surge) clears **one national cut, fixed on the previous
season** — nothing from inside the season being forecast sets it, so the flag is computable a week
at a time. Written to `data/processed/alert_list.parquet` — one row per (facility, week, horizon)
with the probability, the cut and the alert flag. That file is the serving interface; nothing
downstream imports the model.

**Measured at the operating point, h = 1, expanding window, scored within each test year:**

| | test 2025 | test 2024 |
| :--- | ---: | ---: |
| climatology (the baseline to beat) | 0.231 / 0.185 · lift 2.41 | 0.253 / 0.352 · lift 2.65 |
| **this model** | **0.335 / 0.507 · lift 6.63** | **0.447 / 0.722 · lift 5.43** |

(recall / precision, then precision ÷ base rate.) At h = 2: 0.268 / 0.374 · lift 4.89, and
0.412 / 0.632 · lift 4.75. Roughly one alert in two lands on a real surge in 2025 and nearly three
in four in 2024, against 0.185 and 0.352 for the calendar.

**Read lift, not recall, when comparing budget rules.** A prospective cut spends what the season
deserves — 5.1% of facility-weeks in quiet 2025, 8.2% in wave-year 2024 — so recall figures measured
at different spends are not the same measurement. Under the earlier within-year rank at a forced 10%
this model scored 0.306 / 0.245 and 0.393 / 0.547; those numbers remain the ones comparable to `03d`
and are not deployable, because ranking week 30 against week 45 requires week 45 to have happened.

Everything fitted — the climatology, the per-facility scale, the p90 surge threshold — comes from
seasons strictly before the test year. Training rows start post-COVID (2022): a p90 fitted on
post-COVID demand would label almost no earlier week a surge, and pre-COVID seasons carry a seasonal
shape that measurably no longer holds.

### 9.2. What was measured and then collapsed

The three-stage design followed the variance decomposition (`03c`): 60.1% between facilities, 20.5%
seasonal within facility, 13.0% anomaly. The first two are free — a facility identifier and a
calendar produce them — so the model existed to forecast the third, and the third looked like one
national series (`03d`).

It is not that the national series is unforecastable — it is forecastable, at R² 0.772 (h=1) and
0.450 (h=2), leak-free. It is that **forecasting it adds nothing to the alert list**:

| features | 2025 recall | 2024 recall |
| :--- | ---: | ---: |
| all 14 (Stages 1+2+3) | 0.309 | 0.399 |
| drop the national ones | 0.308 | 0.394 |
| **the six above** | **0.306** | **0.393** |
| drop the facility's own history | 0.220 | 0.379 |
| `03d`'s best composition, incl. neighbour rings | 0.313 | 0.396 |

The national anomaly is by construction the cross-facility mean of the very `z` values the
classifier already holds per facility. Stage 1 recovers an average the model can already infer from
the one series that matters to it. Strip the facility's own history instead and the model falls
*below* climatology in 2025.

Two consequences worth stating plainly. First, `03d`'s reported best of 0.321 / 0.428 does not
survive a common scorer — the same features give 0.313 / 0.396 here; that gap was protocol, not
model. Second, Stage 1 retains value as a **reported** figure — "the national wave is rising, R²
0.77 at one week" is a legitimate thing to show an administrator — but it is not load-bearing, and
this document previously claimed it was.

### 9.3. Known limits

- **The serving origin is W−1 and the horizon is h=2.** DEIS publishes with zero lag, but a week is
  only **19.1% complete the day it closes** — 97.8% after seven days, 99.5% after fourteen
  (measured 2026-07-29 from two snapshots eleven days apart; week 28 went 17,311 → 90,574, +423%).
  Backtests read final values; deployment would read a fifth of one, and `z` — the model's dominant
  feature — would register a historic collapse. **Every h=1 figure in this document is a correct
  measurement of a horizon deployment does not have.** The operational numbers are the h=2 ones.
  `load_weekly_target` now trims the unsettled tail for every caller.
- **The alert budget is spent at the peak, not on the ascent, and fixing it is a real trade.** In
  2024 the national cut places 61.3% of its alerts in the five peak weeks (recall 0.727) and 6.5%
  across the fourteen ascent weeks (recall 0.148). Ranking facilities *within* each week raises
  ascent recall to 0.343 and costs 45% of overall lift (5.43 → 2.98), because 42% of the season's
  surges sit in 10% of its calendar and a uniform weekly budget cannot follow that. The union of
  both rules covers ascent *and* peak (0.343 / 0.727, recall 0.547) at 1.7× the budget. **No rule
  dominates**; the choice depends on whether an alert is for anticipation or for triage, which is a
  clinical question the project has not asked.
- **~30% of facilities get no alert at all in a quiet season**, 185 of 609 in 2025 and 66 in 2024.
  Measured cost: **only 3.2% (2025) and 1.1% (2024) of all surges** land in a facility that is never
  warned, and there is no volume bias (median 141 vs 140 weekly attentions). Smaller concern than it
  first appeared; it is a communication question, not a coverage failure.
- **The model produces a ranking, not a probability, and that is structural.** The raw score is
  badly calibrated (top decile 0.569 predicted vs 0.398 observed in 2025; 0.837 vs 0.680 in 2024).
  Isotonic regression on the calibration season was implemented and **made it worse** — mean decile
  gap 0.030 → 0.035 (2025) and 0.058 → 0.210 (2024) — because the surge base rate moves 7.7% to
  13.3% between seasons and *which season it is* is the thing being forecast. A prospectively
  calibrated absolute probability is close to unobtainable here. The served column is therefore
  named `score`, and the interface can honestly show a rank or a within-season percentile, never
  a percentage chance.
- **The cut is calibrated on one prior season.** For test 2024 that season is 2023, itself trained
  on 2022 alone. Thin — and the 2024 spend drifting to 11.4% is what that thinness looks like.
- **The ablation is two holdout years and one seed.** A 0.005 delta is within noise, and there is now
  direct evidence for that: re-running the identical module moves the neighbour-ring variants by
  0.002–0.003 recall (0.318 → 0.315 in 2025), presumably `HistGradientBoostingClassifier`'s threaded
  histogram accumulation. The non-ring rows reproduce exactly. The claim is "the national wave is
  negligible here", not "it is exactly zero".
- **2025 is a quiet season and nothing helps much in it.** 6.9% of facility-weeks above p90 against
  13.4% in 2024. Handed the *realised* national anomaly, the allocation still does not beat the
  calendar in 2025 — in a quiet year the surges that occur are local.

### 9.4. The three stages, as built and measured

#### Stage 1 — the national wave

A single weekly series: the cross-facility mean of standardized facility anomalies. Forecast at
h = 1 and h = 2 from its own recent history (lags 1, 2, 4 and a four-week change), with `RidgeCV`
selecting the regularisation.

**Measured, leak-free:** median within-season out-of-sample R² **0.772** at one week and **0.450** at
two. `03e`'s 0.835 / 0.598 was measured with the climatology fitted on every year *including the
test season* — the anomaly those quantities define is the target, so that is leakage, and no
deployed system can do it. The gap lives entirely in seasons with three or four years of
climatology history; from 2023 on, leaky and leak-free are indistinguishable.

#### Stage 2 — allocation to facilities

Each facility's forecast is its own week-of-year climatology plus its loading on the national
anomaly:

```
demand_hat[i, w] = climatology[i, week_of_year(w)] + beta[i] * national_anomaly_hat[w]
```

A factor model, matching the variance split directly. `beta[i]` is estimated per facility on the
training years, shrunk toward the panel mean for facilities with short history.

**Measured, h = 1:** recall 0.371 vs climatology's 0.253 in 2024 — a large win, precision 0.352 →
0.516. And 0.224 vs 0.231 in 2025, a small loss. Substituting the *realised* national anomaly for
the forecast changes 2025 by 0.004: the failure is not that Stage 1 missed that season, it is that
in a quiet season there is no national signal to allocate.

#### Stage 3 — the alert list

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

**Benchmarks** (surge recall at a fixed budget, h = 1). `03d` reported climatology 0.243 / 0.257 and
a best model of 0.321 / 0.428. Re-derived through `score_alerts` so the numbers are commensurable:
climatology is **0.231 / 0.253** and `03d`'s own feature composition scores **0.313 / 0.396**. Its
reported best does not survive a common scorer. See §9.1 for what ships.

### 9.5. Explicitly excluded

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
│   ├── models/train_model.py        # the whole model: three stages, ablation, alert list
│   └── models/predict_model.py      # empty — write_alert_list covers serving for now
├── services/                       # scaffolded, empty
├── frontend/                       # scaffolded, empty
├── docs/vitalflow-project.md       # this file
├── context/                        # working memory: specs, decisions, handoffs (gitignored)
├── docker-compose.yml              # empty
├── requirements.txt
└── README.md
```

## 11. Immediate Next Steps

Modelling is done and the acceptance criteria are settled — §9.1 for what ships, `train_model.py`
for the numbers. What is left:

1. ~~**Turn the alert budget into a score threshold.**~~ **Done 2026-07-28** — a national P(surge)
   cut fixed on the previous season. The protocol turned out to be pessimistic, not optimistic:
   lift roughly doubles against the calendar. See §9.1 and the decision log entry.
**Re-ordered 2026-07-28 after an end-to-end audit.** The classifier is not the bottleneck. Two of
the three things now blocking a usable product are in the serving layer and one is in the target
definition.

2. ~~**Replace the budget rule with a within-week ranking.**~~ **Measured 2026-07-29 — no rule
   dominates.** Within-week ranking triples ascent recall and costs 45% of lift; the union of it
   and the national cut covers both phases at 1.7× the budget. The national cut stays shipped. The
   open item is now a **clinical question**: is an alert for anticipation or for triage? That
   decides the rule, and no measurement can.
3. ~~**Measure the settling curve.**~~ **Done 2026-07-29.** 19.1% complete at age zero, 97.8% at
   seven days, 99.5% at fourteen. Serving origin W−1, operational horizon h=2, and
   `load_weekly_target` now trims the unsettled tail for every caller.
4. **Calibrate the probability** — isotonic regression on the calibration season already being
   computed. Until then the served column is a score wearing a probability's name.
5. **Run 2026 as a sealed holdout.** 28 weeks, 632 facilities, never used for any decision — the
   feature set, the climatology window and the budget rule were all chosen on 2024 and 2025, which
   are also the years AC2 reports. Write the expected numbers down before running, run once, and do
   not tune on it afterwards.
6. **Test the target against REM20.** Does a week above the facility's own p90 coincide with any
   measurable strain — occupancy, length of stay, diversion? The document is titled *saturation*
   and the target is a demand percentile; these are different constructs and the gap has never been
   measured. A null result is worth having, and it is far cheaper now than after deployment.
7. **Automate the weekly refresh and build the interface**, once 2–4 have settled what is served.
   The refresh must assert tail completeness — refuse to serve on a short week.
8. **Re-check the ablation** when a third holdout year exists. The conclusion that the national
   wave is negligible rests on two years and deltas of 0.005 — the same size as the run-to-run
   noise documented in §9.3.
5. **Only then** revisit covariates, against the filter in §8.2: not seasonal, not static, not
   contemporaneous.
