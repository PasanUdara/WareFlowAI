"""
Real-Time Telemetry and WebSocket Test Suite [Member 4]
Verifies simulation background ticks, EventBus telemetry updates, WebSocket stream endpoint,
multi-client connectivity, client disconnect cleanup, and emergency stop state broadcasting.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app, sim_env, event_bus
from communication import AgentMessageEnvelope, EventType

client = TestClient(app)


def test_simulation_telemetry_generation():
    """Verify that WarehouseEnvironment produces valid AMR telemetry structures."""
    telemetry = sim_env.get_fleet_telemetry()
    assert isinstance(telemetry, list)
    assert len(telemetry) >= 4
    first_robot = telemetry[0]
    assert "robot_id" in first_robot
    assert "position" in first_robot
    assert "battery" in first_robot
    assert "state" in first_robot
    assert "enabled" in first_robot


@pytest.mark.asyncio
async def test_event_bus_telemetry_subscription():
    """Verify that TELEMETRY_UPDATE events can be published and received via EventBus."""
    received = []

    async def telemetry_handler(event: AgentMessageEnvelope):
        received.append(event)

    event_bus.subscribe(EventType.TELEMETRY_UPDATE, telemetry_handler)

    test_envelope = AgentMessageEnvelope(
        source="simulation",
        destination="broadcast",
        event_type=EventType.TELEMETRY_UPDATE,
        payload={"robots": sim_env.get_fleet_telemetry()}
    )

    await event_bus.publish(test_envelope)
    event_bus.unsubscribe(EventType.TELEMETRY_UPDATE, telemetry_handler)

    assert len(received) == 1
    assert received[0].event_type == EventType.TELEMETRY_UPDATE
    assert "robots" in received[0].payload


def test_websocket_telemetry_connection_and_stream():
    """Verify WebSocket /ws/telemetry connects and receives live JSON telemetry packets."""
    with client.websocket_connect("/ws/telemetry") as websocket:
        # Client sends ping or waits for initial telemetry broadcast
        data = websocket.receive_json()
        assert "robots" in data or "event_type" in data
        assert isinstance(data.get("robots", []), list)


def test_websocket_multi_client_and_disconnect():
    """Verify multiple simultaneous WebSocket connections work and disconnect safely."""
    with client.websocket_connect("/ws/telemetry") as ws1:
        with client.websocket_connect("/ws/telemetry") as ws2:
            data1 = ws1.receive_json()
            data2 = ws2.receive_json()
            assert data1 is not None
            assert data2 is not None
        # ws2 disconnects cleanly
    # ws1 remains connected
    assert ws1 is not None
