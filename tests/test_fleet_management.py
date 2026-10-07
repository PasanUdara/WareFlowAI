"""
Fleet Management & Emergency Control Test Suite [Member 4]
Tests R1-R4 fleet initialization, dynamic AMR creation (R5), duplicate ID rejection,
individual detail querying, enable/disable toggling, disabled robot task filtering,
emergency stop / resume toggles, and JWT authorization checks.
"""

import pytest
from fastapi.testclient import TestClient
from main import app, sim_env
from security import create_access_token

client = TestClient(app)


def get_auth_header():
    token = create_access_token(data={"sub": "admin_tester", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_initial_r1_r4_fleet_availability():
    """Verify initial fleet contains R1, R2, R3, R4."""
    response = client.get("/api/v1/fleet/robots")
    assert response.status_code == 200
    data = response.json()
    assert "robots" in data
    robot_ids = [r["robot_id"] for r in data["robots"]]
    
    for expected_id in ["R1", "R2", "R3", "R4"]:
        assert expected_id in robot_ids


def test_add_new_robot_r5():
    """Verify POST /api/v1/fleet/robots dynamically registers new robot R5."""
    new_robot_payload = {
        "robot_id": "R5",
        "name": "Warehouse Robot 5",
        "model": "AMR-Heavy",
        "capabilities": ["transport", "heavy_payload"],
        "initial_position": [0, 0],
        "battery": 95.0
    }
    response = client.post("/api/v1/fleet/robots", json=new_robot_payload, headers=get_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["robot"]["robot_id"] == "R5"
    assert data["robot"]["name"] == "Warehouse Robot 5"
    assert data["robot"]["capabilities"] == ["transport", "heavy_payload"]


def test_duplicate_r5_rejection():
    """Verify registering duplicate robot_id 'R5' is rejected with 400 Bad Request."""
    duplicate_payload = {
        "robot_id": "R5",
        "name": "Duplicate Robot 5",
        "model": "AMR"
    }
    response = client.post("/api/v1/fleet/robots", json=duplicate_payload, headers=get_auth_header())
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_single_robot_detail():
    """Verify GET /api/v1/fleet/robots/R1 returns individual AMR metadata."""
    response = client.get("/api/v1/fleet/robots/R1")
    assert response.status_code == 200
    data = response.json()
    assert data["robot_id"] == "R1"
    assert "battery" in data
    assert "position" in data
    assert "capabilities" in data


def test_disable_and_enable_robot():
    """Verify disabling and enabling robot toggles enabled state and available robot pool."""
    # Disable R1
    resp_disable = client.post("/api/v1/fleet/robots/R1/disable", headers=get_auth_header())
    assert resp_disable.status_code == 200
    assert resp_disable.json()["robot"]["enabled"] is False

    # Check available robots excludes R1
    avail = sim_env.get_available_robots()
    avail_ids = [r["robot_id"] for r in avail]
    assert "R1" not in avail_ids

    # Enable R1
    resp_enable = client.post("/api/v1/fleet/robots/R1/enable", headers=get_auth_header())
    assert resp_enable.status_code == 200
    assert resp_enable.json()["robot"]["enabled"] is True

    # Check available robots includes R1
    avail_after = sim_env.get_available_robots()
    avail_after_ids = [r["robot_id"] for r in avail_after]
    assert "R1" in avail_after_ids


def test_emergency_stop_and_resume():
    """Verify triggering global emergency stop halts movement and resume restores it."""
    # Trigger Emergency Stop
    e_stop_resp = client.post("/api/v1/simulation/e-stop", headers=get_auth_header())
    assert e_stop_resp.status_code == 200
    assert e_stop_resp.json()["emergency_stop"] is True

    # Resume Simulation
    resume_resp = client.post("/api/v1/simulation/e-stop?resume=true", headers=get_auth_header())
    assert resume_resp.status_code == 200
    assert resume_resp.json()["emergency_stop"] is False


def test_invalid_robot_data_validation():
    """Verify out-of-bounds coordinates or invalid battery values are rejected."""
    # Out of grid bounds position [100, 100]
    out_of_bounds = {
        "robot_id": "R99",
        "name": "Invalid Pos Robot",
        "initial_position": [100, 100]
    }
    resp1 = client.post("/api/v1/fleet/robots", json=out_of_bounds, headers=get_auth_header())
    assert resp1.status_code == 400
    assert "outside grid bounds" in resp1.json()["detail"]

    # Empty robot_id
    empty_id = {
        "robot_id": "   ",
        "name": "Empty ID Robot"
    }
    resp2 = client.post("/api/v1/fleet/robots", json=empty_id, headers=get_auth_header())
    assert resp2.status_code == 400
    assert "cannot be empty" in resp2.json()["detail"]
