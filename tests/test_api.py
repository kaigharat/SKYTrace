"""Unit and integration tests for SkyTrace FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["ml_ready"] is True


def test_list_repositories():
    res = client.get("/api/repositories")
    assert res.status_code == 200
    repos = res.json()
    assert isinstance(repos, list)
    assert len(repos) >= 3
    repo_ids = [r["id"] for r in repos]
    assert "repo-orbit-payments" in repo_ids


def test_get_repository_by_id():
    res = client.get("/api/repositories/repo-orbit-payments")
    assert res.status_code == 200
    repo = res.json()
    assert repo["id"] == "repo-orbit-payments"
    assert repo["fullName"] == "acme-labs/orbit-payments"


def test_get_repository_not_found():
    res = client.get("/api/repositories/non-existent-repo-999")
    assert res.status_code == 404


def test_get_repository_health():
    res = client.get("/api/repositories/repo-orbit-payments/health")
    assert res.status_code == 200
    health = res.json()
    assert "score" in health
    assert 0 <= health["score"] <= 100
    assert "breakdown" in health
    assert "riskDistribution" in health


def test_get_components():
    res = client.get("/api/repositories/repo-orbit-payments/components")
    assert res.status_code == 200
    comps = res.json()
    assert len(comps) > 0
    c = comps[0]
    assert "defectRisk" in c
    assert "securityRisk" in c
    assert "metrics" in c
    assert "evidence" in c


def test_get_graph():
    res = client.get("/api/repositories/repo-orbit-payments/graph")
    assert res.status_code == 200
    graph = res.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0


def test_predict_code_validation_error():
    # Missing required 'code' field
    res = client.post("/api/predict/code", json={})
    assert res.status_code == 422


def test_predict_code_success():
    """Verify the ML inference endpoint returns a valid ComponentRisk for a safe snippet."""
    res = client.post("/api/predict/code", json={
        "code": "int add(int a, int b) { return a + b; }",
        "path": "math_utils.c",
        "language": "C",
        "repositoryId": "repo-orbit-payments",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "inferenceSource" in data
    comp = data["component"]
    assert comp["path"] == "math_utils.c"
    assert comp["language"] == "C"
    assert comp["riskLevel"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert 0 <= comp["defectRisk"] <= 100
    assert 0 <= comp["securityRisk"] <= 100
    assert 0 <= comp["regressionRisk"] <= 100
    assert "metrics" in comp
    assert "evidence" in comp
    assert len(comp["evidence"]) > 0


def test_get_security_findings():
    res = client.get("/api/repositories/repo-orbit-payments/security")
    assert res.status_code == 200
    findings = res.json()
    assert isinstance(findings, list)
    assert len(findings) > 0
    f = findings[0]
    assert "severity" in f
    assert "description" in f
    assert f["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_get_pull_requests():
    res = client.get("/api/repositories/repo-orbit-payments/pull-requests")
    assert res.status_code == 200
    prs = res.json()
    assert isinstance(prs, list)
    assert len(prs) > 0
    pr = prs[0]
    assert "title" in pr
    assert "bugRisk" in pr
    assert "securityRisk" in pr
