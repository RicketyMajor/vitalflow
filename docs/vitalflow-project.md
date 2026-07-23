# VitalFlow: Early Warning System for Hospital Emergency Room Saturation

> **Document status.** Revised 2026-07-23 against the actual contents of the repository and the
> datasets on disk. Sections 8–11 previously described intentions as if they were implemented;
> they now separate *what exists* from *what is planned*. Design rationale from the original
> draft is preserved.

## 1. Problem Context
The public health system frequently faces severe saturation in hospital emergency rooms (ERs), particularly during the winter months due to the peak of respiratory viruses. The allocation of medical staff, beds, and critical resources is often reactive, leading to prolonged waiting times, staff burnout, and compromised patient care.

## 2. Justification
Resolving this issue is critical to transition from a reactive healthcare model to a proactive one. Anticipating demand peaks allows hospital administrators to dynamically allocate resources, optimize shift schedules, and redirect non-critical patients to primary care centers, ultimately reducing mortality and improving the overall quality of public health services.

## 3. Clear Problem Definition
The core problem is the inability to accurately forecast the volume and type of emergency room visits at specific health centers in advance. This project seeks to predict the **weekly** influx of respiratory ER patients by correlating historical medical data with external environmental, geographic, and meteorological factors.

## 4. Problem Type
This is a **Multivariate Time Series Forecasting (Regression)** problem over a **panel** of health facilities: the model predicts a continuous count per facility per epidemiological week, from sequences of historical data plus static and future-known covariates.

## 5. Problem Description: Context, Motivation, and Objectives
* **Context:** Healthcare networks operate under constant stress, exacerbated by environmental factors and seasonal epidemics.
* **Motivation:** Building a robust predictive pipeline that demonstrates the practical impact of Data Science and scalable architectures in public health, maximizing the use of local hardware (a 12 GB VRAM GPU) to train deep learning models.
* **Objectives:**
    1. Develop a high-accuracy time series forecasting model with clinical interpretability.
    2. Engineer an automated data pipeline utilizing open government datasets and weather APIs.
    3. Deploy an interactive web application for hospital administrators to visualize forecasted demand and simulate resource allocation.

## 6. Methodology: The Machine Learning Life Cycle (MLOps)

| Phase | Description & Mapping to VitalFlow | Status |
| :--- | :--- | :--- |
| **1. Data Engineering** | Ingestion of DEIS CSV/Parquet datasets and the SINCA air-quality network; PDF extraction of DMC climatological yearbooks; spatial homologation of facilities to monitoring stations. | 🟡 Target complete and audited; exogenous variables not yet joined |
| **2. Modeling** | HDBSCAN catchment clustering, then TFT training on the GPU. Evaluation on RMSE/MAE *and* attention weights for clinical explainability. | 🔴 Not started |
| **3. Deployment & Serving** | Wrapping the trained model in an HTTP API, deployed as an isolated containerized service behind the web backend. | 🔴 Directories scaffolded, empty |
| **4. Monitoring** | Data & model drift tracking; logging predictions against incoming hospital data to trigger retraining. | 🔴 Not started — requires a live DEIS feed that does not yet exist |

## 7. Technology Stack & Real-Time Architecture
The system is designed as a distributed architecture, decoupling the heavy lifting of machine learning inference from the real-time web server operations.

* **Machine Learning Framework:** **PyTorch Forecasting** (built on PyTorch Lightning). Chosen for out-of-the-box support for state-of-the-art time series models and efficient VRAM management.
* **Inference Backend (Worker):** **FastAPI (Python)**. Serves the trained model, kept loaded in memory.
* **Web Server & Real-Time Engine:** **Node.js + Express + Socket.io**. Handles authentication, serves the frontend map, and pushes saturation alerts over WebSockets.
* **Message Broker:** **Redis (Pub/Sub)**. Bridges Node.js and FastAPI, queueing prediction requests so concurrent demand does not overwhelm the Python worker.

> **Implementation reality (2026-07-23).** Only the data-engineering half of this stack is installed:
> pandas, numpy, scipy, statsmodels, scikit-learn, duckdb, pyarrow, geopy, matplotlib, seaborn and
> the profiling libraries. `torch` and `pytorch-forecasting` are **not** installed. HDBSCAN needs no
> new dependency — `sklearn.cluster.HDBSCAN` ships with the installed scikit-learn 1.9.
> `services/` and `frontend/` contain no code, and `docker-compose.yml` is empty.

## 8. Data

### 8.1. Target variable

**Source:** `data/raw/Atenciones de Urgencia/Atenciones de urgencias de causas respiratorias por semana epidemiológica/at_urg_respiratorio_semanal.parquet` (DEIS / MINSAL).

**Definition:** `OrdenCausa = 3` — *TOTAL CAUSA SISTEMA RESPIRATORIO (J00-J98)*, weekly count per facility.

| Property | Value |
| :--- | :--- |
| Granularity | Epidemiological week × facility |
| Coverage | 2014 – week 27 of 2026 |
| Facilities | 632 |
| Rows | 3,583,168 |

The taxonomy is strictly hierarchical and was verified empirically: sub-causes `OrdenCausa` 4–9
(IRA Alta, Influenza, Neumonía, Bronquitis/bronquiolitis, Crisis obstructiva bronquial, Otra causa
respiratoria) sum to `OrdenCausa = 3` **exactly**, with zero drift across 56,072,767 events.

> ⚠ **Do not select causes by text matching.** `OrdenCausa = 33` is labelled
> *"- Causas sistema respiratorio (J00-J98)"* and is a **hospitalization** subtotal, not an ER
> attention. A `LIKE '%RESPIRATORIO%'` predicate captures it and silently inflates the target. This
> defect existed in the earlier daily pipeline; see the decision log entry of 2026-07-23.

This dataset also carries the static attributes the model needs, with no join required:
`RegionGlosa`, `ComunaGlosa`, `ServicioSaludGlosa`, `TipoEstablecimiento`, `DependenciaAdministrativa`,
`NivelAtencion`, `TipoUrgencia`, `NivelComplejidad`, `Latitud`, `Longitud`.

**Alternative considered and rejected as primary:** the daily dataset
(`data/processed/urgencias_parquet/`, 817 facilities, 2017–2024) offers finer granularity but stops
18 months before the present, carries no facility metadata, and loses 83 facilities to a fragile
coordinate join. Weekly resolution is adequate for surge planning, matches how Chilean epidemiological
surveillance already operates, and reaches the current week.

### 8.2. Exogenous variables

| Source | What it provides | Coverage | Status |
| :--- | :--- | :--- | :--- |
| **SINCA (MMA)** | MP2.5 / MP10 daily concentrations, 199 stations | 2023 – 2025 | Scraped and processed; **never joined to the target** |
| **DMC yearbooks** | Monthly climatological variables, 165 canonical stations | 2005 – 2025 | Extracted to tidy long format; not joined |
| **CR2 Explorador Climático** | Alternative climate series | — | Downloaded, unused |
| **INE Censo 2024 / DPA** | Comunal geometries and administrative codes | 2024 | Downloaded, unused |
| **IGVUST** | Socio-territorial vulnerability index per comuna | — | Downloaded, unused; strong candidate static feature |
| **DEIS REM20** | Hospitalisation process indicators | to 2026-06 | Downloaded, unused; candidate capacity proxy |

> **Not used, contrary to the original draft:** ARCLIM and Boostr are named in the earlier version of
> this document but appear nowhere in the codebase and were never ingested. The real weather source
> is the DMC yearbook PDF pipeline.

> **Serving gap.** No exogenous source currently reaches 2026, while the target does. A model that
> depends on pollution or weather covariates cannot be served today without a live SINCA/DMC feed.
> This must be resolved before deployment, not after.

### 8.3. Known data hazards

These are established facts from the audit in `notebooks/03_eda_comprehensive.ipynb`, not risks:

1. **COVID structural break.** ER attendance collapsed in 2020 (−65% vs 2019) and 2021 (−51%), then
   overshot in 2022. This is genuine demand collapse, not under-reporting: *more* facilities reported
   in 2020 than in 2019. Any model spanning 2020–2021 needs an explicit regime indicator, or those
   years must be excluded.
2. **Extreme skew and kurtosis.** Raw daily counts show skewness 6.35 and excess kurtosis 822; the
   1–4 age band reaches excess kurtosis 112,140. A variance-stabilising transform is mandatory.
   The **cube root** was selected over `log1p` after benchmarking every zero-tolerant candidate.
3. **Exact accounting identity.** The five age bands sum to the total in 100% of rows, giving VIF = ∞.
   Model the total **or** the decomposition, never both.
4. **Unbalanced panel.** Facilities enter and leave the register over time; an unreported week is not
   a zero-demand week and must be masked, not imputed as zero.
5. **Dirty categorical metadata.** The static attributes need normalisation before use as cluster or
   model features — they contain whitespace and case variants that would fragment categories
   silently: `"Municipal"` vs `"Municipal "` (418 vs 13 facilities),
   `"Urgencia Ambulatoria (SAR)"` vs `"Urgencia ambulatoria (SAR)"` (80 vs 6), plus placeholder
   values `"Completar"` and `"Pendiente"`.
6. **Invalid coordinates.** `hospital_sinca_dmc_mapping.csv` contains a nearest-neighbour distance of
   3,509 km — impossible in Chile — and genuine mojibake in 1,739 of 4,025 facility names
   (`MÃ©dico` → `Médico`). Both are handled in `src/data/make_dataset.py`.

## 9. Algorithms

### 9.1. Spatial Clustering (Data Preparation): HDBSCAN
* **Role:** Unsupervised learning applied during data engineering.
* **Function:** Rather than assigning patients to hospitals by administrative borders (comunas),
  HDBSCAN groups facilities by density to approximate organic catchment areas, producing a static
  categorical feature for the forecasting network. It finds the cluster count on its own and labels
  low-density points as noise, which suits an irregular, coast-hugging national geography.
* **Candidate feature space (undecided):** geographic coordinates; facility typology (complexity,
  care level, administrative dependency); mean environmental profile; or a combination. The decision
  is pending and is tracked in `context/specs/spatial-clustering-hdbscan.md`.
* **Correction to the original draft:** an earlier version claimed HDBSCAN would cluster
  "demographic densities". No demographic density variable exists in the pipeline. IGVUST is the
  closest available proxy and remains unused.

### 9.2. Predictive Engine: Temporal Fusion Transformer (TFT)
* **Role:** The core deep learning architecture for multivariate panel forecasting.
* **Function:** The TFT handles heterogeneous inputs simultaneously — observed covariates
  (pollution and weather history), static covariates (facility complexity, cluster label, region),
  and known-future covariates.
* **Clinical Interpretability:** Attention weights are emitted alongside each prediction, letting an
  administrator see *why* saturation is forecast rather than accepting a black-box number.
* **Consequence of weekly granularity:** day-of-week and weekend indicators — cited as example
  future-known covariates in the original draft — do not exist at this resolution. The usable
  known-future covariates are epidemiological week, month, seasonal harmonics, school-holiday periods
  and public-holiday counts per week.

## 10. Repository Structure (actual)

```text
vitalflow/
├── data/                           # local only, gitignored — see context/sources/index.md
│   ├── raw/                        # DEIS, SINCA, DMC, CR2, INE, IGVUST
│   ├── processed/                  # Parquet conversions, station mappings
│   └── external/
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 01b_csv_to_parquet_duckdb.ipynb    # CSV → Parquet via DuckDB
│   ├── 01c_sinca_python_scraper.ipynb     # Python rewrite of the original R scraper
│   ├── 02_feature_engineering.ipynb       # stale: predates the target correction
│   ├── 03_eda_comprehensive.ipynb         # statistical audit (executed)
│   ├── 03_spatial_clustering_hdbscan.ipynb  # empty
│   └── 04_tft_model_baseline.ipynb          # empty
├── src/
│   ├── data/make_dataset.py        # canonical loaders + self-check
│   ├── features/build_features.py  # empty stub
│   └── models/{train,predict}_model.py  # empty stubs
├── services/                       # scaffolded, empty
│   ├── ml_worker/  web_server/  broker/
├── frontend/                       # scaffolded, empty
├── docs/vitalflow-project.md       # this file
├── context/                        # working memory: specs, decisions, handoffs (gitignored)
├── docker-compose.yml              # empty
├── requirements.txt
└── README.md
```

## 11. Immediate Next Steps
1. Rebuild the target pipeline on the weekly dataset in `src/data/make_dataset.py`, with categorical
   normalisation and a COVID regime flag.
2. Join SINCA and DMC to the target and run the exogenous EDA — **the project's central hypothesis,
   that air quality predicts respiratory ER demand, has never been tested.** Measure correlation,
   optimal lag structure, and collinearity among exogenous variables.
3. Decide the HDBSCAN feature space on that evidence, then cluster.
4. Establish the TFT baseline.
