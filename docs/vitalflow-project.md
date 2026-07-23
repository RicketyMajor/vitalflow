# VitalFlow: Early Warning System for Hospital Emergency Room Saturation

## 1. Problem Context
The public health system frequently faces severe saturation in hospital emergency rooms (ERs), particularly during the winter months due to the peak of respiratory viruses. The allocation of medical staff, beds, and critical resources is often reactive, leading to prolonged waiting times, staff burnout, and compromised patient care.

## 2. Justification
Resolving this issue is critical to transition from a reactive healthcare model to a proactive one. Anticipating demand peaks allows hospital administrators to dynamically allocate resources, optimize shift schedules, and redirect non-critical patients to primary care centers, ultimately reducing mortality and improving the overall quality of public health services.

## 3. Clear Problem Definition
The core problem is the inability to accurately forecast the volume and type of emergency room visits at specific health centers in advance. This project seeks to predict the daily influx of ER patients by correlating historical medical data with external environmental, geographic, and meteorological factors.

## 4. Problem Type
This is a **Multivariate Time Series Forecasting (Regression)** problem. The model will predict continuous numerical values (expected number of patients per day/week) based on sequences of historical data and future covariates.

## 5. Problem Description: Context, Motivation, and Objectives
* **Context:** Healthcare networks operate under constant stress, exacerbated by environmental factors and seasonal epidemics.
* **Motivation:** Building a robust predictive pipeline that demonstrates the practical impact of Data Science and scalable architectures in public health, maximizing the use of local hardware (such as a 12GB VRAM GPU) to train deep learning models.
* **Objectives:** 
    1. Develop a high-accuracy time series forecasting model with clinical interpretability.
    2. Engineer an automated data pipeline utilizing open government datasets and weather APIs.
    3. Deploy an interactive web application for hospital administrators to visualize forecasted demand and simulate resource allocation.

## 6. Methodology: The Machine Learning Life Cycle (MLOps)
To ensure the project evolves from a static analysis into a scalable software product, VitalFlow adopts the **ML Life Cycle** framework. This guarantees modularity and smooth integration between the data engineering, modeling, and real-time serving phases.

| Phase | Description & Mapping to VitalFlow |
| :--- | :--- |
| **1. Data Engineering** | **Automated Ingestion & Processing:** Fetching CSV datasets (MINSAL) and querying APIs (DMC, ARCLIM, Boostr). Cleaning and transforming geo-coordinates into continuous spatial features. |
| **2. Modeling** | **Training & Evaluation:** Designing the deep learning architecture. Utilizing the GPU to train the model iteratively. Evaluating not just accuracy metrics (RMSE, MAE), but also analyzing attention weights for clinical explainability. |
| **3. Deployment & Serving** | **Microservices Orchestration:** Wrapping the trained model in a high-performance HTTP API. Deploying it as an isolated containerized service that listens to the main web application backend. |
| **4. Monitoring** | **Data & Model Drift Tracking:** Logging real-time predictions against actual incoming hospital data to monitor performance degradation over time and trigger retraining pipelines. |

## 7. Technology Stack & Real-Time Architecture
The system is designed as a distributed architecture, decoupling the heavy lifting of machine learning inference from the real-time web server operations.

* **Machine Learning Framework:** **PyTorch Forecasting** (built on PyTorch Lightning). Chosen for its out-of-the-box support for state-of-the-art time series models and its highly efficient VRAM management, allowing maximization of local GPU resources.
* **Inference Backend (Worker):** **FastAPI (Python)**. Serves the trained PyTorch model. It stays loaded in memory and rapidly processes prediction requests.
* **Web Server & Real-Time Engine:** **Node.js + Express + Socket.io**. Handles user authentication, serves the frontend map application, and pushes real-time saturation alerts to the client's browser via WebSockets.
* **Message Broker:** **Redis (Pub/Sub)**. Acts as the communication bridge between Node.js and FastAPI. It manages asynchronous task queues, ensuring that if multiple hospitals request predictions simultaneously, the Python worker doesn't crash but processes them sequentially or distributes them.

## 8. Data and Algorithms

### 8.1. Data Sources
* **Health & Location:** Emergency Attention Records and Health Center Geolocation (DEIS - MINSAL). Target variable ($y$) and anchor points.
* **Environmental Exogenous Variables:** Air Quality Monitoring Network (SINCA - MMA) for MP2.5/MP10 lags, and Climatological APIs (DMC / ARCLIM / Boostr) for historical and real-time weather features.

### 8.2. Analytical & Predictive Models
The project utilizes a two-step modeling approach:

**A. Spatial Clustering (Data Preparation): HDBSCAN**
* **Role:** Unsupervised learning algorithm used during the data engineering phase. 
* **Function:** Instead of assigning patients to hospitals based on arbitrary political borders (comunas), HDBSCAN clusters geographical coordinates and demographic densities to define the true, organic "catchment areas" (áreas de influencia) of each emergency room. This provides a clean, density-based spatial feature for the predictive network.

**B. Predictive Engine: Temporal Fusion Transformer (TFT)**
* **Role:** The core deep learning architecture for multivariate forecasting.
* **Function:** Replaces traditional sequential models like LSTMs. The TFT is specifically designed to handle heterogeneous inputs simultaneously (e.g., historical pollution lags, static hospital locations, and known future inputs like weekends or holidays). 
* **Clinical Interpretability:** Unlike "black box" models, TFT uses attention mechanisms that output explicit weights, allowing administrators to see *why* a saturation is predicted (e.g., "70% driven by recent MP2.5 spikes").

## 9. Complete Project Structure
```text
vitalflow/
├── data/
│   ├── raw/                        # Raw downloaded datasets (DEIS, SINCA)
│   ├── processed/                  # Cleaned datasets and HDBSCAN cluster outputs
│   └── external/                   # GeoJSON files for mapping
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_spatial_clustering_hdbscan.ipynb
│   └── 04_tft_model_baseline.ipynb
├── src/
│   ├── data/                       # Automated ingestion scripts (APIs + Scraping)
│   ├── models/                     # PyTorch Forecasting architectures
│   └── utils/                      # Helper functions
├── services/                       # Microservices Backend
│   ├── ml_worker/                  # FastAPI app holding the TFT model
│   ├── web_server/                 # Node.js + Express application
│   └── broker/                     # Redis configuration
├── frontend/                       # React / Vue.js UI with real-time mapping
├── docker-compose.yml              # Local orchestration (DB, Node, FastAPI, Redis)
└── README.md
```