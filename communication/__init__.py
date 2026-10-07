"""
Communication Package [Member 4]
Provides inter-agent message protocol models and asynchronous pub/sub event bus.
"""

from .protocol import AgentMessageEnvelope, EventType, MessagePriority, MCPMessage
from .event_bus import AsyncEventBus, get_event_bus

__all__ = [
    "AgentMessageEnvelope",
    "EventType",
    "MessagePriority",
    "MCPMessage",
    "AsyncEventBus",
    "get_event_bus",
]

