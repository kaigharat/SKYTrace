"""End-to-End flow test verifying the complete user-to-prediction lifecycle:
User Code Input -> API Request -> Validation -> ML Preprocessing -> Model Inference ->
Prediction -> Backend Response -> Frontend Types Compatibility.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_complete_prediction_flow():
    """Validates the entire prediction flow end-to-end."""
    sample_code = """
    void handle_transaction(char* transaction_id, double amount) {
        char buffer[32];
        if (amount < 0) {
            return;
        }
        // Vulnerable unchecked copy
        strcpy(buffer, transaction_id);
        gets(buffer);
        process_payment(buffer, amount);
    }
    """

    payload = {
        "code": sample_code,
        "path": "billing/transaction.c",
        "language": "C",
        "repositoryId": "repo-orbit-payments",
    }

    # Step 1: Send request to FastAPI endpoint
    response = client.post("/api/predict/code", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["status"] == "success"
    assert "inferenceSource" in data

    comp = data["component"]
    # Step 2: Validate returned ComponentRisk data structure
    assert comp["path"] == "billing/transaction.c"
    assert comp["language"] == "C"
    assert comp["riskLevel"] in ("HIGH", "CRITICAL")
    assert comp["securityRisk"] >= 50
    assert comp["defectRisk"] > 0
    assert comp["regressionRisk"] > 0

    # Step 3: Validate metrics
    metrics = comp["metrics"]
    assert metrics["loc"] > 5
    assert metrics["cyclomaticComplexity"] >= 2  # Has if branch
    assert metrics["coupling"] >= 1

    # Step 4: Validate explainability evidence
    evidence = comp["evidence"]
    assert len(evidence) > 0
    evidence_labels = [e["label"] for e in evidence]
    assert any("Unsafe" in label for label in evidence_labels)

    # Step 5: Verify that the analyzed component is recorded in repository state
    res_list = client.get("/api/repositories/repo-orbit-payments/components")
    assert res_list.status_code == 200
    all_paths = [c["path"] for c in res_list.json()]
    assert "billing/transaction.c" in all_paths

    # Step 6: Verify repository health was updated
    res_health = client.get("/api/repositories/repo-orbit-payments/health")
    assert res_health.status_code == 200
    health = res_health.json()
    assert health["highRiskComponentCount"] >= 1
