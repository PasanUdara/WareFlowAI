"""
LangGraph Node: escalate_to_human [Member 1]
Handles the case where no robot was available to fulfil the task.
Sets status="escalated" and logs the event for supervisor notification.
"""

import logging
from typing import Any, Dict

from agents.task_planning.state import TaskPlanningState

logger = logging.getLogger(__name__)


def escalate_to_human(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Escalate an unassignable task to a human warehouse supervisor.

    Logs full context so the ops team can take manual action.
    """
    order_text = state.get("order_text", "")
    subtasks = state.get("subtasks") or []

    logger.warning(
        "ESCALATION — no robot available. Order: '%s' | Subtasks: %d",
        order_text,
        len(subtasks),
    )

    return {"status": "escalated"}
