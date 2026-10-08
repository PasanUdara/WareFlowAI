"""
Test Suite for Member 2 Exception Handling & Anomaly Injection Endpoints
Verifies JWT authentication enforcement, anomaly injection states,
dynamic obstacle clearance, and active exception inspection endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app, sim_env
from security import create_access_token

client = TestClient(app)


def get_auth_header():
    token = create_access_token(data={"sub": "operator_tester", "role": "operator"})
    return {"Authorization": f"Bearer {token}"}


def test_inject_anomaly_endpoint_rejects_invalid_token():
    """Verify POST /api/v1/simulation/robots/{id}/inject-anomaly rejects invalid tokens with 401."""
    response = client.post(
        "/api/v1/simulation/robots/R1/inject-anomaly",
        json={"anomaly_type": "stuck"},
        headers={"Authorization": "Bearer invalid_secret_token_12345"}
    )
    assert response.status_code == 401
    assert "Invalid or expired authentication token" in response.json()["detail"]


def test_inject_anomaly_endpoint_with_auth_stuck():
    """Verify POST /api/v1/simulation/robots/{id}/inject-anomaly triggers stuck state when authenticated."""
    response = client.post(
        "/api/v1/simulation/robots/R1/inject-anomaly",
        json={"anomaly_type": "stuck"},
        headers=get_auth_header()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["details"]["anomaly_type"] == "ROBOT_STUCK"
    assert sim_env.robots["R1"].state.value == "STUCK"
    assert sim_env.robots["R1"].stuck_duration >= 10.0


def test_inject_anomaly_endpoint_with_auth_low_battery():
    """Verify POST /api/v1/simulation/robots/{id}/inject-anomaly drains battery below critical threshold."""
    response = client.post(
        "/api/v1/simulation/robots/R2/inject-anomaly",
        json={"anomaly_type": "low_battery"},
        headers=get_auth_header()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["details"]["anomaly_type"] == "LOW_BATTERY"
    assert sim_env.robots["R2"].battery <= 15.0


def test_inject_anomaly_block_path_and_clear():
    """Verify dynamic obstacle injection and clearing."""
    response = client.post(
        "/api/v1/simulation/robots/R3/inject-anomaly",
        json={"anomaly_type": "block_path"},
        headers=get_auth_header()
    )
    assert response.status_code == 200
    assert len(sim_env.dynamic_blocked_cells) > 0

    # Clear obstacles
    clear_resp = client.post(
        "/api/v1/simulation/obstacles/clear",
        headers=get_auth_header()
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["success"] is True
    assert len(sim_env.dynamic_blocked_cells) == 0


def test_invalid_anomaly_type_rejection():
    """Verify rejection of unsupported anomaly types with 400 Bad Request."""
    response = client.post(
        "/api/v1/simulation/robots/R1/inject-anomaly",
        json={"anomaly_type": "teleportation"},
        headers=get_auth_header()
    )
    assert response.status_code == 400
    assert "Unsupported anomaly type" in response.json()["detail"]


def test_get_active_exception_endpoint():
    """Verify GET /api/v1/simulation/exceptions/active returns lifecycle state."""
    response = client.get("/api/v1/simulation/exceptions/active")
    assert response.status_code == 200
    data = response.json()
    assert "lifecycle" in data
    assert "blocked_cells" in data
    assert isinstance(data["blocked_cells"], list)
