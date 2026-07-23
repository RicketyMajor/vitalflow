# VitalFlow: Early Warning System for Hospital Emergency Room Saturation

VitalFlow is a predictive analytics project designed to forecast the volume and type of emergency room (ER) visits at specific health centers. By correlating historical medical data with external environmental, geographic, and meteorological factors, the system aims to help hospital administrators dynamically allocate resources and optimize operations, transitioning from a reactive to a proactive public healthcare model.

## Core Objectives

1. Develop a high-accuracy multivariate time series forecasting model using a Temporal Fusion Transformer (TFT).
2. Engineer an automated data pipeline utilizing open government datasets and weather APIs.
3. Deploy an interactive web application for hospital administrators to visualize forecasted demand and simulate resource allocation.

## Architecture and Technology Stack

The project adopts a distributed architecture to separate heavy machine learning inference from real-time web server operations:

* **Machine Learning Framework:** PyTorch Forecasting (Temporal Fusion Transformer)
* **Inference Backend:** FastAPI (Python worker for model serving)
* **Web Server & Real-Time Engine:** Node.js, Express, Socket.io
* **Message Broker:** Redis (Pub/Sub for communication between Node.js and FastAPI)
* **Data Processing:** DuckDB (for memory-efficient out-of-core aggregations)

## Current Project Status

The project is currently in the Data Engineering and Exploratory Data Analysis (EDA) phase. 
* The target variables (Respiratory Urgencies) have been aggregated and analyzed.
* Data skewness has been normalized.
* We are currently defining the feature space for the spatial clustering phase using HDBSCAN, which will define organic catchment areas for each emergency room before training the TFT model.

## Project Structure

* `data/`: Raw, processed, and external datasets.
* `notebooks/`: Jupyter notebooks for data exploration, feature engineering, clustering, and baseline modeling.
* `src/`: Python source code for data ingestion, models, and utility functions.
* `services/`: Microservices backend containing the machine learning worker, web server, and broker configuration.
* `frontend/`: User interface with real-time mapping capabilities.
* `context/`: Project specifications, architectural decisions, and handoff documentation.

## Getting Started

*(Detailed setup instructions will be provided as the project stabilizes)*

To set up the initial Python environment for data exploration:

1. Create a virtual environment and activate it.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Docker Compose is available for orchestrating the microservices stack locally:
   ```bash
   docker-compose up -d
   ```

## License and Documentation

Detailed documentation regarding architectural decisions, models, and specifications can be found in the `docs/` and `context/` directories.
