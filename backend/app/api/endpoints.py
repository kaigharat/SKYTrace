"""FastAPI routers implementing the REST API and ML integration contracts."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.domain import (
    AnalysisJob,
    AnalysisStep,
    CommitEntry,
    ComponentRisk,
    PredictCodeRequest,
    PredictCodeResponse,
    PullRequestReview,
    Repository,
    RepositoryGraph,
    RepositoryHealth,
    SecurityFinding,
)
from backend.app.services.repo_service import get_repo_service

router = APIRouter()


# ==================== Health & System ====================

@router.get("/health", tags=["System"])
def health_check():
    """System health status."""
    return {"status": "healthy", "service": "SkyTrace Repository Intelligence API", "ml_ready": True}


# ==================== Repositories ====================

@router.get("/repositories", response_model=List[Repository], tags=["Repositories"])
def list_repositories():
    """List all connected repositories."""
    service = get_repo_service()
    return service.get_all_repositories()


@router.post("/repositories/connect", response_model=Repository, status_code=status.HTTP_201_CREATED, tags=["Repositories"])
def connect_repository(payload: dict):
    """
    Connect a GitHub repository and kick off real analysis.
    Accepts: { "fullName": "owner/repo" } or { "fullName": "https://github.com/owner/repo" }
    """
    service = get_repo_service()
    full_name = payload.get("fullName") or payload.get("name") or ""
    description = payload.get("description", "")

    if not full_name:
        raise HTTPException(status_code=422, detail="fullName is required (e.g. 'owner/repo' or GitHub URL)")

    try:
        repo = service.connect_and_analyze(full_name, description)
        return repo
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect repository: {e}")


@router.get("/repositories/{repo_id}", response_model=Repository, tags=["Repositories"])
def get_repository(repo_id: str):
    """Retrieve repository metadata by ID."""
    service = get_repo_service()
    repo = service.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found")
    return repo


@router.post("/repositories/{repo_id}/analyze", response_model=AnalysisJob, tags=["Repositories"])
def analyze_repository(repo_id: str):
    """Trigger or re-trigger an analysis run on a repository."""
    service = get_repo_service()
    repo = service.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found")

    # Re-trigger analysis
    service._start_analysis(repo_id, repo.fullName)
    job = service.get_analysis_status(repo_id)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to start analysis")
    return job


@router.get("/repositories/{repo_id}/analyze/status", response_model=AnalysisJob, tags=["Repositories"])
def get_analysis_status(repo_id: str):
    """Get real-time analysis job status. Poll this endpoint during analysis."""
    service = get_repo_service()
    job = service.get_analysis_status(repo_id)
    if not job:
        # Check if repo exists
        repo = service.get_repository(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail=f"Repository {repo_id} not found")
        # Return a completed job for already-analyzed repos
        return AnalysisJob(
            repositoryId=repo_id,
            status=repo.analysisStatus,
            progress=100 if repo.analysisStatus == "completed" else 0,
            startedAt=repo.connectedAt,
            steps=[],
        )
    return job


@router.get("/repositories/{repo_id}/health", response_model=RepositoryHealth, tags=["Repositories"])
def get_repository_health(repo_id: str):
    """Retrieve calculated repository health score, trends, and risk distributions."""
    service = get_repo_service()
    health = service.get_health(repo_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Health metrics not found for {repo_id}. Analysis may still be running.")
    return health


# ==================== Components & Code Risk ====================

@router.get("/repositories/{repo_id}/components", response_model=List[ComponentRisk], tags=["Components"])
def list_components(repo_id: str):
    """List analyzed components and risk scores for a repository."""
    service = get_repo_service()
    return service.get_components(repo_id)


@router.get("/repositories/{repo_id}/components/{component_id}", response_model=ComponentRisk, tags=["Components"])
def get_component_risk(repo_id: str, component_id: str):
    """Retrieve detailed risk scores, metrics, explainability factors, and similar historical patterns."""
    service = get_repo_service()
    comp = service.get_component(repo_id, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Component {component_id} not found in {repo_id}")
    return comp


@router.get("/repositories/{repo_id}/components/{component_id}/code", tags=["Components"])
def get_component_code(repo_id: str, component_id: str):
    """Retrieve source code preview for a component."""
    service = get_repo_service()
    code = service.get_code_snippet(component_id)
    return {"componentId": component_id, "code": code}


@router.get("/repositories/{repo_id}/components/{component_id}/history", response_model=List[CommitEntry], tags=["Components"])
def get_component_history(repo_id: str, component_id: str):
    """Retrieve commit history for a component."""
    service = get_repo_service()
    return service.get_commit_history(component_id)


# ==================== Dependency Graph ====================

@router.get("/repositories/{repo_id}/graph", response_model=RepositoryGraph, tags=["Graphs"])
def get_repository_graph(repo_id: str):
    """Retrieve the interactive dependency and call graph for a repository."""
    service = get_repo_service()
    graph = service.get_graph(repo_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph not found for {repo_id}")
    return graph


# ==================== Security Findings ====================

@router.get("/repositories/{repo_id}/security", response_model=List[SecurityFinding], tags=["Security"])
def get_security_findings(repo_id: str):
    """Retrieve security vulnerabilities identified by static analysis and ML risk models."""
    service = get_repo_service()
    return service.get_security_findings(repo_id)


# ==================== Pull Requests ====================

@router.get("/repositories/{repo_id}/pull-requests", response_model=List[PullRequestReview], tags=["Pull Requests"])
def list_pull_requests(repo_id: str):
    """List AI-reviewed pull requests for a repository."""
    service = get_repo_service()
    return service.get_pull_requests(repo_id)


@router.get("/pull-requests/{pr_id}", response_model=PullRequestReview, tags=["Pull Requests"])
def get_pull_request_review(pr_id: str):
    """Retrieve an individual PR risk review, affected blast radius, and test recommendations."""
    service = get_repo_service()
    pr = service.get_pull_request(pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail=f"Pull request review {pr_id} not found")
    return pr


# ==================== Live ML Prediction Flow ====================

@router.post("/predict/code", response_model=PredictCodeResponse, tags=["ML Inference"])
def predict_code(request: PredictCodeRequest):
    """
    Executes the real ML inference pipeline on the provided source code:
    1. Extracts 39 static features
    2. Runs RandomForestBaseline model
    3. Computes multi-dimensional risk scores
    4. Generates explainable EvidenceFactors
    5. Matches similar historical vulnerability patterns
    """
    service = get_repo_service()
    comp = service.analyze_code_snippet(
        code=request.code,
        path=request.path,
        language=request.language,
        repo_id=request.repositoryId,
        component_id=request.componentId,
    )
    return PredictCodeResponse(
        component=comp,
        inferenceSource="SkyTrace RandomForest ML Baseline + 39 Static Features",
        status="success",
    )
