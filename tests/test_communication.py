"""
Unit and Event Bus Tests [Member 4]
Verifies AgentMessageEnvelope model creation, EventType enums, and AsyncEventBus async pub/sub functionality.
"""

import pytest
import asyncio
from communication import AgentMessageEnvelope, EventType, MessagePriority, AsyncEventBus, get_event_bus


def test_agent_message_envelope_creation():
    """Verify envelope initialization and default UUID/timestamp generation."""
    envelope = AgentMessageEnvelope(
        source="task_planning",
        destination="exception_handling",
        event_type=EventType.TASK_DISPATCHED,
        payload={"order_id": "ORD-123"}
    )
    assert envelope.message_id is not None
    assert envelope.source == "task_planning"
    assert envelope.destination == "exception_handling"
    assert envelope.event_type == EventType.TASK_DISPATCHED
    assert envelope.payload["order_id"] == "ORD-123"
    assert envelope.priority == MessagePriority.NORMAL
    assert envelope.status == "sent"


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Verify async event subscription and handler invocation."""
    bus = AsyncEventBus()
    received_events = []

    async def sample_handler(event: AgentMessageEnvelope):
        received_events.append(event)

    bus.subscribe(EventType.ORDER_RECEIVED, sample_handler)

    test_event = AgentMessageEnvelope(
        source="gateway",
        destination="task_planning",
        event_type=EventType.ORDER_RECEIVED,
        payload={"order_text": "Fetch 2 medical kits"}
    )

    await bus.publish(test_event)

    assert len(received_events) == 1
    assert received_events[0].message_id == test_event.message_id
    assert received_events[0].payload["order_text"] == "Fetch 2 medical kits"


@pytest.mark.asyncio
async def test_event_bus_handler_error_isolation():
    """Verify that a failing handler does not crash other subscribers or the publisher."""
    bus = AsyncEventBus()
    successful_calls = []

    async def failing_handler(event: AgentMessageEnvelope):
        raise ValueError("Handler crash simulation!")

    async def working_handler(event: AgentMessageEnvelope):
        successful_calls.append(event)

    bus.subscribe(EventType.ANOMALY_DETECTED, failing_handler)
    bus.subscribe(EventType.ANOMALY_DETECTED, working_handler)

    test_event = AgentMessageEnvelope(
        source="simulation",
        destination="exception_handling",
        event_type=EventType.ANOMALY_DETECTED,
        payload={"robot_id": "R1", "anomaly": "STUCK"}
    )

    # Publish should complete without raising the inner handler ValueError
    await bus.publish(test_event)

    assert len(successful_calls) == 1
    assert successful_calls[0].payload["robot_id"] == "R1"


@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    """Verify handler unsubscription."""
    bus = AsyncEventBus()
    calls = []

    def handler(event: AgentMessageEnvelope):
        calls.append(event)

    bus.subscribe(EventType.TELEMETRY_UPDATE, handler)
    bus.unsubscribe(EventType.TELEMETRY_UPDATE, handler)

    await bus.publish(AgentMessageEnvelope(
        source="simulation",
        event_type=EventType.TELEMETRY_UPDATE,
        payload={}
    ))

    assert len(calls) == 0
