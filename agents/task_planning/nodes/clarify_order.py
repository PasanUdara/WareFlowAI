"""
LangGraph Node: clarify_order [Member 1]
Handles the case where order parsing failed (malformed LLM output or
unintelligible order text).  Sets status="needs_clarification" so the
calling system knows to request a revised order from the user / ERP.
"""

import logging
from typing import Any, Dict

from agents.task_planning.state import TaskPlanningState

logger = logging.getLogger(__name__)


def clarify_order(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Mark the task as needing clarification from the order source.

    This is the terminal node reached when parse_order cannot produce
    a valid structured order.
    """
    order_text = state.get("order_text", "")

    logger.warning(
        "CLARIFICATION NEEDED — could not parse order: '%s'",
        order_text[:120],
    )

    return {"status": "needs_clarification"}
