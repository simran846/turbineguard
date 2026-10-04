"""Integration tests for FastAPI REST endpoints."""

import pytest
from fastapi.testclient import TestClient

from turbineguard.api.main import app

client = TestClient(app)


@pytest.mark.integration
def test_api_health_endpoint():
    """Verifies GET /health returns 200 OK and valid payload."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "TurbineGuard" in data["service"]


@pytest.mark.integration
def test_api_simulation_run_and_status():
    """Verifies POST /simulation/start runs simulation and updates status."""
    payload = {
        "duration_s": 5.0,
        "wind_scenario": "constant",
        "base_wind_speed_ms": 11.5
    }
    res = client.post("/simulation/start", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["data_points"] > 0
    assert "metrics" in data

    # Check status endpoint
    status_res = client.get("/simulation/status")
    assert status_res.status_code == 200
    assert status_res.json()["total_data_points"] == data["data_points"]


@pytest.mark.integration
def test_api_fault_injection_endpoint():
    """Verifies POST /faults/inject schedules a failure mode."""
    payload = {
        "fault_type": "RotorOverspeed",
        "start_time_s": 2.0,
        "duration_s": 3.0,
        "severity": "CRITICAL"
    }
    res = client.post("/faults/inject", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SCHEDULED"
    assert data["fault"]["fault_type"] == "RotorOverspeed"


@pytest.mark.integration
def test_api_list_faults():
    """Verifies GET /faults returns supported and active faults."""
    res = client.get("/faults")
    assert res.status_code == 200
    data = res.json()
    assert len(data["supported_faults"]) >= 9


@pytest.mark.integration
def test_api_validation_run_endpoint():
    """Verifies POST /validation/run executes verification and returns reports."""
    res = client.post("/validation/run")
    assert res.status_code == 200
    data = res.json()
    assert data["total_requirements"] >= 10
    assert data["pass_rate_pct"] >= 90.0
    assert "reports" in data
    assert "html" in data["reports"]
