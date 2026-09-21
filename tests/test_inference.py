"""Unit tests for SkyTrace ML Feature Extraction and Inference Engine."""

import pytest
from backend.ml.features.static_features import FEATURE_NAMES, extract_features
from backend.ml.inference.engine import InferenceEngine, get_inference_engine


def test_static_feature_names_count():
    """Verify all 39 static features are extracted."""
    feats = extract_features("int main() { return 0; }")
    assert len(FEATURE_NAMES) == 39
    for name in FEATURE_NAMES:
        assert name in feats, f"Missing feature {name}"


def test_static_feature_extraction_empty():
    """Empty code should return valid dictionary with 0 LOC."""
    feats = extract_features("")
    assert feats["n_lines"] == 0
    assert feats["length_chars"] == 0
    assert feats["has_strcpy"] == 0.0


def test_dangerous_function_detection():
    """Vulnerable function patterns must be flagged."""
    code = "void vuln(char* s) { char b[10]; strcpy(b, s); gets(b); free(b); }"
    feats = extract_features(code)
    assert feats["has_strcpy"] == 1.0
    assert feats["has_gets"] == 1.0
    assert feats["has_free"] == 1.0


def test_inference_engine_safe_prediction():
    """Safe functions should receive LOW risk level."""
    engine = get_inference_engine()
    safe_code = """
    int calculate_square(int x) {
        return x * x;
    }
    """
    pred = engine.predict_code(safe_code, path="math.c", language="C")
    assert pred.riskLevel in ("LOW", "MEDIUM")
    assert pred.securityRisk < 40
    assert pred.defectRisk < 40
    assert pred.metrics.loc > 0
    assert pred.metrics.cyclomaticComplexity == 1
    assert len(pred.evidence) > 0


def test_inference_engine_vulnerable_prediction():
    """Vulnerable function with unchecked copy must trigger HIGH or CRITICAL risk."""
    engine = get_inference_engine()
    vuln_code = """
    void handle_packet(char* packet) {
        char buf[16];
        strcpy(buf, packet);
        gets(buf);
        sprintf(buf, "%s", packet);
    }
    """
    pred = engine.predict_code(vuln_code, path="packet.c", language="C")
    assert pred.riskLevel in ("HIGH", "CRITICAL")
    assert pred.securityRisk >= 50
    # Must provide explainability evidence
    evidence_labels = [e.label for e in pred.evidence]
    assert any("Unsafe" in label for label in evidence_labels)
