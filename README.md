<div align="center">

# ☁️ SkyTrace
### Repository Intelligence AI

**Understand your software repository as a connected ML system.**

[![Branch](https://img.shields.io/badge/branch-V1-blue?style=flat-square)](https://github.com/kaigharat/SKYTrace/tree/V1)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=nextdotjs)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

> BTech Deep Learing Software Engineering Project

</div>

---

## What is SkyTrace?

Modern software repositories are complex, inter-connected systems. Standard static linters evaluate code **in isolation**, missing systemic risks.

**SkyTrace** bridges this gap by unifying:
- 🌳 **Source Code AST semantics** — structural parse trees per component
- 🔗 **Dependency & Call Graphs** — import and call relationships as a DAG
- 📜 **Git Commit History** — churn, bug-fix patterns, and co-change clusters
- 🤖 **Machine Learning Models** — Random Forest / XGBoost trained on defect data

…into a **single intelligence layer** that predicts defect risks, identifies security vulnerabilities, and highlights regression blast radius across your entire codebase.

---

## ✨ Core Capabilities

| Module | Description |
|---|---|
| 📊 **Repository Health Score** | Aggregated 0–100 score with 14-day trend, risk distribution breakdown |
| 🔍 **Component Risk Analysis** | Per-file/function/class defect probability, cyclomatic complexity, coupling |
| 🕸️ **Dependency Graph** | Interactive DAG showing imports, calls, inheritance, and blast radius hops |
| 🔒 **Security Findings** | Semgrep + ML vulnerability scoring with line-level evidence traces |
| 🔀 **PR Impact Review** | AI-powered blast radius analysis, regression heatmap, and test recommendations |
| 🧠 **Historical Defect Intelligence** | FAISS vector search matching components against past bug patterns |
| ⚡ **Live ML Inference API** | Real-time `/predict/code` endpoint — 39 static features → risk score |

---

## 🏗️ Architecture

```
User (Browser)
     │
     ▼
┌─────────────────────────┐
│   Next.js 16 Frontend   │  React 19 · Tailwind CSS · shadcn/ui · Recharts
│   (Port 3000)           │
└───────────┬─────────────┘
            │ REST API calls
            ▼
┌─────────────────────────┐
│   FastAPI Backend       │  Python 3.11 · Pydantic · Uvicorn
│   (Port 8000)           │
└──────┬──────────┬───────┘
       │          │
       ▼          ▼
 GitHub API    ML Engine
 (PyGithub)    │
               ├─ AST Parser       (ast / tree-sitter)
               ├─ Feature Extractor (39 static features)
               ├─ RF/XGBoost Model  (joblib weights)
               └─ FAISS Index       (defect vector search)
```

### Data Pipeline

```
GitHub Repo URL
      │
      ▼ Clone & Ingest
Source Files + Git History
      │
      ▼ Parse
AST Trees · Import Graphs · Commit Logs · PR Diffs
      │
      ▼ Feature Extraction
Cyclomatic Complexity · Code Churn · Coupling · LOC · Change Frequency
      │
      ▼ ML Inference
Random Forest / XGBoost → Defect Probability [0.0 – 1.0]
      │
      ▼ Risk Classification
LOW · MEDIUM · HIGH · CRITICAL  +  Explainable Evidence Factors
      │
      ▼ Dashboard
Interactive Graphs · PR Reviews · Security Findings
```

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** — async REST API framework
- **PyGithub** — GitHub repository data ingestion
- **scikit-learn / XGBoost** — ML defect prediction models
- **FAISS** — vector similarity search for historical defect matching
- **Pydantic v2** — strict schema validation and serialization

### Frontend
- **Next.js 16** (App Router) — SSR + React Server Components
- **React 19** — UI layer
- **Tailwind CSS** + **shadcn/ui** — component system
- **Recharts** — health trend and risk distribution charts

### Infrastructure
- **Docker Compose** — one-command full-stack deployment
- **Pytest** — API, ML, and E2E test suites

---

## 🚀 Getting Started

### Prerequisites

- Python **3.11+**
- Node.js **18+** and npm/pnpm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/kaigharat/SKYTrace.git
cd SKYTrace
git checkout V1
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your GitHub token *(strongly recommended)*:

```env
GITHUB_TOKEN=ghp_your_token_here        # github.com/settings/tokens
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> **Without a token:** 60 API requests/hour (public repos only)  
> **With a token:** 5,000 requests/hour + private repo support

### 3. Start the Backend

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r backend/requirements.txt

# Run the API server
python scripts/start_backend.py
# → API available at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# → App available at http://localhost:3000
```

### 5. Docker (Full Stack)

```bash
docker-compose up --build
# Backend → http://localhost:8000
# Frontend → http://localhost:3000
```

---

## 📡 API Reference

Base URL: `http://localhost:8000/api`  
Interactive docs: [`/docs`](http://localhost:8000/docs) (Swagger UI)

### Repositories

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/repositories` | List all connected repositories |
| `POST` | `/repositories/connect` | Connect a GitHub repo and trigger analysis |
| `GET` | `/repositories/{id}` | Get repository metadata |
| `POST` | `/repositories/{id}/analyze` | Re-trigger analysis |
| `GET` | `/repositories/{id}/analyze/status` | Poll real-time analysis progress |
| `GET` | `/repositories/{id}/health` | Get health score, trends, risk distribution |

### Components & Code

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/repositories/{id}/components` | List all analyzed components with risk scores |
| `GET` | `/repositories/{id}/components/{cid}` | Detailed risk, metrics, and evidence for one component |
| `GET` | `/repositories/{id}/components/{cid}/code` | Source code preview |
| `GET` | `/repositories/{id}/components/{cid}/history` | Commit history for a component |

### Graphs, Security & PRs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/repositories/{id}/graph` | Full dependency/call graph (nodes + edges) |
| `GET` | `/repositories/{id}/security` | Security vulnerability findings |
| `GET` | `/repositories/{id}/pull-requests` | AI-reviewed pull request list |
| `GET` | `/pull-requests/{pr_id}` | Individual PR blast radius + test recommendations |

### ML Inference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/predict/code` | Live inference: submit code → get risk score + evidence |

**Example `/predict/code` request:**
```json
{
  "code": "def authenticate(user, password):\n    query = f'SELECT * FROM users WHERE name={user}'",
  "path": "auth/service.py",
  "language": "Python",
  "repositoryId": "my-repo"
}
```

---

## 📁 Project Structure

```
SKYtrace/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints.py       # All REST API routes
│   │   ├── schemas/
│   │   │   └── domain.py          # Pydantic domain models
│   │   └── services/
│   │       ├── repo_service.py    # Core analysis orchestration
│   │       └── github_service.py  # GitHub API integration
│   └── ml/
│       ├── data/
│       │   └── dataset.py         # Training data loader (parquet splits)
│       └── weights/
│           └── rf_baseline.joblib # Trained Random Forest model
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Landing page
│   │   ├── onboarding/            # Repository connection flow
│   │   └── (app)/repositories/
│   │       └── [repoId]/          # Repository dashboard + component pages
│   ├── components/
│   │   ├── layout/                # App shell, nav, theme toggle
│   │   ├── pr-review/             # PR blast radius UI
│   │   └── shared/                # Health ring, risk badge, logo
│   └── lib/
│       ├── api.ts                 # Typed API client
│       ├── types.ts               # TypeScript domain types
│       └── risk.ts                # Risk level helpers
├── tests/
│   ├── test_api.py
│   ├── test_e2e_flow.py
│   ├── test_pr_blast_radius.py
│   ├── test_inference.py
│   └── ml/
│       ├── test_dataset.py
│       └── test_phase1.py
├── scripts/
│   ├── start_backend.py           # Development server launcher
│   └── dev.sh                     # Full-stack dev helper
├── docker-compose.yml
├── .env.example
└── conftest.py
```

---

## 🧪 Running Tests

```bash
# All tests
pytest

# API tests only
pytest tests/test_api.py -v

# ML pipeline tests
pytest tests/ml/ -v

# End-to-end flow
pytest tests/test_e2e_flow.py -v
```

---

## 🎯 Risk Levels

SkyTrace classifies every component across three risk dimensions:

| Level | Badge | Threshold | Action |
|---|---|---|---|
| 🟢 **LOW** | `LOW` | Probability < 0.30 | Monitor periodically |
| 🟡 **MEDIUM** | `MEDIUM` | 0.30 – 0.55 | Review before release |
| 🔴 **HIGH** | `HIGH` | 0.55 – 0.75 | Prioritize refactor |
| 🚨 **CRITICAL** | `CRITICAL` | > 0.75 | Block PR / immediate fix |

Health score weights: **Defect Risk** 30% · **Security Risk** 30% · **Regression Risk** 20% · **Code Quality** 10% · **Historical Stability** 10%

---

## 👥 Team

| Role | Name | Responsibility |
|---|---|---|
| Product · Frontend · GitHub Intelligence | **Yashodhan** | UI/UX, landing page, repo integration |
| AI / ML · Research | **Swarali** | Model training, FAISS, feature engineering |
| Backend · Infrastructure | **Kaivalya** | FastAPI, services, deployment |

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">
  <sub>Built with ❤️ as a BTech Final-Year Software Engineering Project</sub><br/>
  <sub>Next.js 16 · React 19 · FastAPI · Python ML · Tailwind CSS · shadcn/ui</sub>
</div>
