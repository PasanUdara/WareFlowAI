"""
Communication Package [Member 4]
Provides inter-agent message protocol models and asynchronous pub/sub event bus.
"""

from .protocol import AgentMessageEnvelope, EventType, MessagePriority
from .event_bus import AsyncEventBus, get_event_bus

__all__ = [
    "AgentMessageEnvelope",
    "EventType",
    "MessagePriority",
    "AsyncEventBus",
    "get_event_bus",
]
