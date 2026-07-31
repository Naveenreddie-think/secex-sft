from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extract_endpoint_success():
    fake_result = {
        "success": True,
        "extraction": {
            "vulnerabilities": [{
                "cve_id": None,
                "affected_products": [],
                "cwe_category": "Test Category",
                "severity": "high",
                "attack_vector": "network",
                "impact_summary": "Test impact.",
                "remediation_action": "Upgrade.",
            }]
        },
        "groundedness_warnings": [],
    }

    with patch("app.routers.extract.extract", return_value=fake_result):
        response = client.post("/extract", json={"input_text": "Some advisory text."})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["extraction"]["vulnerabilities"][0]["severity"] == "high"
    assert data["groundedness_warnings"] == []


def test_extract_endpoint_handles_model_failure():
    fake_result = {
        "success": False,
        "error": "Model endpoint request failed: connection timeout",
    }

    with patch("app.routers.extract.extract", return_value=fake_result):
        response = client.post("/extract", json={"input_text": "Some advisory text."})

    assert response.status_code == 200  # endpoint itself succeeds; failure is in the payload
    data = response.json()
    assert data["success"] is False
    assert "timeout" in data["error"]


def test_extract_endpoint_requires_input_text():
    response = client.post("/extract", json={})
    assert response.status_code == 422  # Pydantic validation error, missing required field