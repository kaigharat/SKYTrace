# SkyTrace Backend & ML Service

FastAPI-powered repository intelligence backend integrated with the SkyTrace Machine Learning inference engine.

## Overview

The SkyTrace backend provides:
1. **REST API Endpoints**: Endpoints specified in the PRD for repositories, component risks, dependency/call graphs, pull requests, and security findings.
2. **Machine Learning Pipeline**: Real-time static feature extraction (39 source code features) and classification via `RandomForestBaseline` (and CodeBERT / Multimodal architectures).
3. **Explainability Engine**: Feature attribution identifying why code components are categorized as high-risk (e.g. unsafe memory functions, elevated cyclomatic complexity, excessive coupling).
4. **Repository Intelligence Service**: Aggregates component-level predictions into composite repository health scores and risk distributions.

## Structure

```text
backend/
├── app/
│   ├── api/          # FastAPI routers (endpoints.py)
│   ├── core/         # Configuration & CORS settings (config.py)
│   ├── schemas/      # Pydantic data contracts (domain.py)
│   ├── services/     # Business logic & repository store (repo_service.py)
│   └── main.py       # FastAPI application entrypoint
├── ml/
│   ├── features/     # Static (39 features), history, and graph builders
│   ├── inference/    # Production inference engine (engine.py)
│   ├── models/       # Model architectures (RandomForestBaseline, CodeBERT, Multimodal)
│   ├── weights/      # Serialized model weights (rf_baseline.joblib)
│   ├── configs/      # Experiment & training configs (YAML)
│   ├── reports/      # Training metrics, ROC curves, ablation studies
│   └── scripts/      # Model training, dataset generation, ranking evaluation
├── requirements.txt  # Python dependencies
└── Dockerfile
```

## Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger documentation will be available at:
`http://localhost:8000/docs`
