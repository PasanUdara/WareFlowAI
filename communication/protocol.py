"""
Communication Protocol Module [Member 4]
Defines common message and event envelope models, EventType enum, and priorities
for inter-agent communication.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Supported inter-agent and system event types."""
    ORDER_RECEIVED = "ORDER_RECEIVED"
    TASK_CREATED = "TASK_CREATED"
    TASK_DISPATCHED = "TASK_DISPATCHED"
    ROBOT_ASSIGNED = "ROBOT_ASSIGNED"
    TELEMETRY_UPDATE = "TELEMETRY_UPDATE"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    RECOVERY_ACTION = "RECOVERY_ACTION"
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"
    COMPLIANCE_APPROVED = "COMPLIANCE_APPROVED"
    COMPLIANCE_REJECTED = "COMPLIANCE_REJECTED"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SYSTEM_RESUMED = "SYSTEM_RESUMED"


class MessagePriority(str, Enum):
    """Priority levels for message handling."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AgentMessageEnvelope(BaseModel):
    """
    Standard envelope format for inter-agent communication and system events.
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = Field(..., description="Agent or module triggering the event", example="task_planning")
    destination: str = Field("broadcast", description="Target agent or module ID", example="exception_handling")
    event_type: EventType = Field(..., description="Type of event being communicated")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: Optional[str] = Field(None, description="Optional ID tracking multi-step workflows")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured event payload data")
    priority: MessagePriority = Field(MessagePriority.NORMAL, description="Event processing priority")
    status: str = Field("sent", description="Current delivery or processing status")

    class Config:
        use_enum_values = True
