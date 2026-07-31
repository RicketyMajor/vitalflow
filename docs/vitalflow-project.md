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

**Measured on the product's own population — 180 hospital emergency departments — h = 1, expanding
window, scored within each test year:**

| | test 2026 *(sealed)* | test 2025 | test 2024 |
| :--- | ---: | ---: | ---: |
| surge base rate | 0.055 | 0.070 | 0.108 |
| climatology (the baseline to beat) | 0.212 / 0.109 · lift 1.98 | 0.184 / 0.150 · lift 2.13 | 0.174 / 0.304 · lift 2.81 |
| **this model** | **0.500 / 0.457 · lift 8.31** | **0.464 / 0.498 · lift 7.06** | **0.403 / 0.686 · lift 6.35** |
| **margin over climatology** | **4.20×** | **3.32×** | **2.26×** |

(recall / precision, then precision ÷ base rate, then the ratio of the two lifts.) At h = 2:
0.282 / 0.284 · lift 5.19 · margin **2.69×** (2026); 0.334 / 0.329 · lift 4.66 · margin 2.20×
(2025); 0.309 / 0.620 · lift 5.73 · margin 2.04× (2024).

Restricting from all 632 facilities to the 180 that can act on an alert *improves* the product, and
did so again on the sealed season: the full panel scores lift 6.63 (2025), 5.43 (2024) and 6.23
(2026) at h = 1, with margins of 2.85×, 2.05× and 2.78×. The earlier full-panel figures are retained
here because §9.2's ablation and §9.4's stage tables are computed on them.

**Reproducibility — fixed 2026-07-30; read §9.3's last bullet before quoting any digit here.** These
figures now reproduce bit for bit across processes and thread settings, and the whole table above was
re-pinned when the fix landed. The cause was a missing `ORDER BY` in the data loader, not the model, and
`OMP_NUM_THREADS=1` is no longer part of the protocol. What the fix did **not** remove is the
sensitivity it exposed: permuting the row order moves 2026 h=1 lift across **7.94–8.31**. Quote two
significant figures, not three; the h=2 column and every acceptance criterion are stable across the
whole envelope.

### 9.1b. The metric was measuring the easy half of the target

**Every figure in the table above is 52–64% composed of surge *continuation*, and continuation needs no
model.** This was found by auditing the holdout rather than by running it, and it is the most important
qualification in this document.

Split each surge week by whether it is new:

| | definition | share of all surge weeks |
| :--- | :--- | ---: |
| **onset** | above p90 at the target week, **not** above it the week before | 36% (2024), 44% (2025), **48% (2026)** |
| **continuation** | above p90 at the target week **and** the week before | the rest |

A shift coordinator can see an ongoing surge from the waiting room. **Onset is what an early-warning
system is for**, and it is the harder half. So the comparator has to be a rule that exploits
continuation and nothing else: **alert next week iff this facility is above its p90 this week** — one
line, no training, no features.

**On the aggregate metric this project has reported since day one, that one-liner beats the shipped
model** — in 2025 and in the sealed 2026, at equal or lower spend (2026 h=2: recall 0.315 vs 0.282,
precision 0.333 vs 0.284, at 5.2% against 5.4%). A zero-parameter rule beating the model means the metric
is wrong, not that the model is worthless — and splitting the truth set shows why.

**At matched spend** (every rule given the model's own alert count, ranked top-N):

| season | h | onset recall: climatology | **this model** | persistence | continuation recall: model / persistence |
| ---: | ---: | ---: | ---: | ---: | :--- |
| 2024 | 1 | **0.139** | 0.109 | 0.000 | 0.567 / 0.676 |
| 2024 | 2 | 0.117 | 0.117 | 0.061 | 0.416 / 0.446 |
| 2025 | 1 | 0.121 | **0.173** | 0.000 | 0.693 / 0.970 |
| 2025 | 2 | 0.128 | **0.217** | 0.200 | 0.427 / 0.614 |
| **2026** *(sealed)* | **1** | 0.137 | **0.221** | 0.046 | 0.755 / 1.000 |
| **2026** *(sealed)* | **2** | 0.131 | **0.162** | 0.108 | 0.392 / 0.517 |

*Printed by `demo()`; reproduce with `python src/models/train_model.py` — since 2026-07-30 that is
bit-reproducible without a thread setting.*

**This is the model's real result, and it is a better one than the headline.** At a fixed budget it
identifies roughly **60% more new surges than the seasonal calendar** and four to five times as many as
persistence, on a season used for no decision. It beats the calendar in **4 of 6** season×horizon cells,
**ties** 2024 h=2 and loses 2024 h=1, and beats persistence in **6 of 6**. The cleaner statement of the
same table: it wins **both horizons of both post-2024 seasons** and does not beat the calendar in 2024 at
all. Persistence scores **0.000 at h=1 by construction** — it cannot flag a surge that has not begun — so
its aggregate win is won entirely on the half that does not need forecasting.

> **Corrected 2026-07-30.** This paragraph read "**5 of 6** cells, losing only 2024 h=1" until the
> reproducibility fix re-pinned the table. The 2024 h=2 cell was 0.119 against the calendar's 0.117 and is
> now 0.117 against 0.117 — the win was one thousandth wide and did not survive a change of row order.
> Nothing about the model changed. This is the clearest available illustration of why this document now
> quotes two significant figures: a *count of cells won* is a hard threshold, and a hard threshold on a
> narrow gap inherits the full width of the envelope in §9.3.

**All of the above is computed and asserted by `train_model.py`**, not by a one-off script:
`score_alerts` returns `onset_recall` and `contin_recall` alongside the aggregate, `alert_frame` carries
the `onset` and `surge_now` columns, `prospective_alerts` reports the persistence baseline, `demo()`
prints this table and **asserts that the shipped model beats persistence on new surges at h=1 in all
three seasons**, and the served `alert_list.parquet` carries `observed_onset`. The assertion is
deliberately restricted to h=1, where the margin is the width of persistence's structural zero
(0.109–0.221 against 0.000–0.046) and is far wider than the row-order envelope in §9.3; the 2025 h=2
cell is a genuine 0.217 against 0.200, but 0.017 is inside that envelope and is not assertable.

**Consequences for how this document should be read.** Onset recall is the primary metric from here on,
reported alongside the aggregate and never without matched spend. The aggregate figures in §9.1 stand as
correct measurements of a quantity that overstates early-warning skill. Persistence joins climatology as
a permanent baseline; climatology alone is too weak a comparator, and this document previously implied
that beating it settled the question.

*One caution recorded so it is not rediscovered: at each rule's **natural** spend, climatology appears to
beat the model on 2026 onset recall, 0.305 against 0.221. That is a spend artefact — it fires 533 alerts
against 300. At matched budget it reverses. Compare only at matched spend; the table above does.*

*Not tested, deliberately: climatology and the model catch **different** onsets, so a union or a
re-weighting may raise onset recall materially. Testing it on 2026 would be tuning on the sealed season.
It is a hypothesis for a future season.*

**Read lift, not recall, when comparing budget rules — and neither when comparing seasons.** A
prospective cut spends what the season deserves — 5.1% of facility-weeks in quiet 2025, 8.2% in
wave-year 2024, 6.1% in 2026 — so recall figures measured at different spends are not the same
measurement. Under the earlier within-year rank at a forced 10% this model scored 0.306 / 0.245 and
0.393 / 0.547 on the full panel; those numbers remain the ones comparable to `03d` and are not
deployable, because ranking week 30 against week 45 requires week 45 to have happened.

**Across seasons, lift is the wrong figure and the margin is the right one.** `lift = precision ÷
base_rate`, and the base rate is the season's severity — the very thing being forecast. The 2026
column shows the trap directly: lift *rises* from 7.06 to 7.95 while precision *falls* from 0.498 to
0.437, because the base rate fell further (0.070 → 0.055). The margin cancels the shared denominator
and reduces to precision(model) ÷ precision(climatology), so it compares seasons honestly. This was
learned by falsifying a pre-registered prediction rather than by reasoning — the 2026 holdout
predicted a lift of 5.0 with a ceiling of 7.5, and the mechanism behind that prediction was wrong.

**The 2026 column is a sealed holdout and is the strongest claim in this document.** Features, the
climatology window, the alert cut and the hospital scope were all selected on 2024 and 2025; 2026 was
never consulted for any decision. The protocol, expected numbers and falsification thresholds were
pre-registered in `context/specs/2026-sealed-holdout.md`, the test was run once against a pinned
snapshot (2026-07-29, 5,006 facility-weeks, weeks 1–28), all four acceptance criteria were met, and
nothing was adjusted afterwards. It validates the pipeline, not the construct — see §9.3.

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
- **A third of hospital emergency departments hear nothing in a quiet season.** On the product's own
  scope: **65 of 180 in 2026** at h=1 and 48 of 180 in 2025, against 22 in wave-year 2024. The
  pre-registered holdout expected 10–50 and this is the one prediction that missed in the unfavourable
  direction. It follows from the 6% realised spend rather than from a modelling defect — a cut fixed on
  a quiet season, applied to a quieter one, simply fires less. The earlier measurement that silent
  facilities cost only 3.2% (2025) and 1.1% (2024) of all surges, with no volume bias, was taken on the
  **full 609-facility panel** and does not transfer to this scope: it has not been re-measured on the
  180, and a quiet sealed season is exactly where it would be weakest. **Open.** An interface that must
  tell a third of its hospitals "nothing this winter" needs to know what those facilities' surges
  actually were before it is designed.
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
  0.002–0.003 recall (0.318 → 0.315 in 2025). The claim is "the national wave is negligible here",
  not "it is exactly zero".
- **The fit was not reproducible across processes. Fixed 2026-07-30 — and the cause was in the data
  loader, three files upstream of the model.** `load_weekly_target` ran DuckDB's parallel `GROUP BY ALL`
  with no `ORDER BY`, so the aggregate emitted its groups in thread-scheduling order and **every process
  received the same 318,810 rows in a different sequence** (measured: three processes, three different
  row-order hashes, one identical order-independent value hash). Every `groupby` mean and std downstream
  then accumulated in that order, so the fitted climatology, scale and `z` differed in their last bits —
  and that is enough, because a boosted tree compares split gains as floats: a tie broken the other way
  changes a split, the tree below it, the probabilities, and the calibration-season quantile that sets
  the alert cut. One `ORDER BY EstablecimientoCodigo, Anio, SemanaEstadistica` closes it, and
  `build_features.demo()` now asserts the returned frame is sorted so it cannot silently regress.
  **Two prior claims in this bullet were wrong and are corrected by the fix.** The mechanism was *not*
  threaded histogram accumulation in `HistGradientBoostingClassifier`, and **`OMP_NUM_THREADS=1` was
  never doing anything**: repeated calls inside one process agreed because they shared one data load, not
  because threads were pinned. With the ordering fixed, default multi-threaded and single-threaded runs
  in separate processes now agree to six decimals. The diagnostic recorded here — true positives stable
  at 131 while alerts moved 300 → 294 — pointed correctly at the calibration season's probabilities.
- **What the fix did not remove: the model is genuinely sensitive to row order, and that sets the
  precision at which any digit here may be quoted.** Permuting the panel (same data, same seed, same
  everything) still gives 2026 h=1 lift **7.94–8.31**, recall **0.478–0.500**, onset recall
  **0.191–0.221**, silent facilities **65–72**; the amplifier is arithmetic, not modelling — 274 surges
  in 4,984 rows at a ~6% spend means six surges crossing the cut moves recall by 0.022. The pinned order
  is now *a* deterministic draw from that envelope, not a distinguished one. **So: two significant
  figures, never three.** h=2 is markedly tighter (lift 5.16–5.19), every acceptance criterion holds
  across the whole envelope, and one §9.1b conclusion did not — see the correction note there, where a
  cell count of "5 of 6" rested on a gap of 0.002 and is now 4 of 6. Narrowing the envelope itself
  (averaging several seeds into one score) is untested and belongs to whoever needs a third decimal.
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

Modelling and validation are done — §9.1 for what ships, §9.1b for the metric that judges it,
`train_model.py` for the numbers. What is left:

0. ~~**Make the pipeline reproducible.**~~ **Done 2026-07-30, and it was the data loader, not the
   model.** A parallel `GROUP BY` with no `ORDER BY` handed every process a different row order; the
   fitted quantities differed in their last bits and that was enough to move the alert cut. One `ORDER
   BY`, one assert, and every figure in this document now reproduces bit for bit across processes and
   thread settings — `OMP_NUM_THREADS=1`, which never actually did anything, is retired. §9.3.
   **The residual is a sensitivity, not a bug:** permuting the row order still moves 2026 h=1 lift across
   7.94–8.31, so this document quotes two significant figures. Publishing outside the repository is no
   longer blocked, provided nothing is quoted to three decimals.

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
4. ~~**Calibrate the probability.**~~ **Tried 2026-07-29 and rejected — it makes calibration worse.**
   Isotonic regression on the calibration season moved the mean decile gap 0.030 → 0.035 (2025) and
   0.058 → 0.210 (2024), for the structural reason in §9.3: the base rate moves between seasons and
   *which season it is* is the forecast target. The served column is named `score`, and the interface
   may show a rank or a within-season percentile — never a percentage chance.
5. ~~**Run 2026 as a sealed holdout.**~~ **Run 2026-07-29, once, and it passed all four acceptance
   criteria.** 28 settled weeks over the 180 hospital emergency departments, against a pinned snapshot,
   pre-registered in `context/specs/2026-sealed-holdout.md` before the data was touched. h=2 lift 5.19
   against climatology 1.92 — margin 2.69×, floor 2× — and h=1 beat the baseline on both recall and
   precision. **The selection risk is retired:** the feature set, the climatology window, the budget
   rule and the hospital scope were all chosen on 2024 and 2025, and the ranking transfers to a season
   none of them saw, at the best margin of the three. Two by-products matter more than the pass: lift
   is not comparable across seasons (§9.1), and the fit was not reproducible — root-caused and fixed
   the next day, in the data loader rather than the model (§9.3, item 0 above).
6. **Test the target against REM20.** Does a week above the facility's own p90 coincide with any
   measurable strain — occupancy, length of stay, diversion? This is the open question the holdout
   explicitly does not answer: it validated the pipeline, not the construct. Scoped 2026-07-29 by
   inspecting the file — hospital emergency departments only (179 of 180 join; 0 of 446 ambulatory),
   at facility-month granularity, with `INDICE_OCUPACIONAL` as the primary outcome. A null result is
   worth having, and it is far cheaper now than after deployment.
   **`IdCausa = 34` ("TOTAL DEMANDA")** is the parallel lead: an unexamined daily-file row running 8.5%
   above total attentions, which — if it is unmet demand — is the capacity denominator this project has
   never held, and the only one that would exist for the ambulatory facilities.
7. **Automate the weekly refresh and build the interface**, once 2–4 have settled what is served.
   The refresh must assert tail completeness — refuse to serve on a short week.
8. **Re-check the ablation** when a third holdout year exists. The conclusion that the national
   wave is negligible rests on two years and deltas of 0.005 — the same size as the run-to-run
   noise documented in §9.3.
9. **Only then** revisit covariates, against the filter in §8.2: not seasonal, not static, not
   contemporaneous.
