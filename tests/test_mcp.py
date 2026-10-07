"""
MCP (Model Context Protocol) JSON-RPC 2.0 Test Suite [Member 4]
Verifies JSON-RPC 2.0 tool listing, tool calling, error handling, and agent integration.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from security import create_access_token

client = TestClient(app)


def get_auth_header():
    token = create_access_token(data={"sub": "mcp_tester", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_mcp_tools_list():
    """Verify JSON-RPC tools/list method returns registered tools."""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-1",
        "method": "tools/list",
        "params": {}
    }
    response = client.post("/api/v1/mcp/rpc", json=payload, headers=get_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-1"
    assert "result" in data
    tools = data["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "task_planner.dispatch" in tool_names
    assert "compliance.check" in tool_names
    assert "exception.reroute" in tool_names
    assert "fleet.telemetry" in tool_names


def test_mcp_task_planner_dispatch():
    """Verify MCP tools/call for task_planner.dispatch executes Member 1 agent."""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-2",
        "method": "tools/call",
        "params": {
            "name": "task_planner.dispatch",
            "arguments": {
                "order_text": "Move 3 pallets from Shelf B1 to Packing Station 2"
            }
        }
    }
    response = client.post("/api/v1/mcp/rpc", json=payload, headers=get_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == "test-2"
    assert "result" in data
    assert data["result"]["success"] is True
    assert data["result"]["assigned_robot_id"] is not None


def test_mcp_compliance_check():
    """Verify MCP tools/call for compliance.check executes Member 3 agent."""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-3",
        "method": "tools/call",
        "params": {
            "name": "compliance.check",
            "arguments": {
                "payload_weight": 10.0,
                "speed": 1.0,
                "is_hazmat": False,
                "target_zone": "Zone-A"
            }
        }
    }
    response = client.post("/api/v1/mcp/rpc", json=payload, headers=get_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "result" in data
    assert data["result"]["is_compliant"] is True


def test_mcp_fleet_telemetry():
    """Verify MCP tools/call for fleet.telemetry returns active AMR telemetry."""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-4",
        "method": "tools/call",
        "params": {
            "name": "fleet.telemetry"
        }
    }
    response = client.post("/api/v1/mcp/rpc", json=payload, headers=get_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "robots" in data["result"]
    assert len(data["result"]["robots"]) > 0


def test_mcp_unknown_method():
    """Verify unknown MCP method returns standard JSON-RPC error."""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-5",
        "method": "unknown/invalid_method",
        "params": {}
    }
    response = client.post("/api/v1/mcp/rpc", json=payload, headers=get_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == -32601
    assert "not recognized" in data["error"]["message"]
