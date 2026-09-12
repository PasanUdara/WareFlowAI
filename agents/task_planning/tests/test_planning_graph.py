"""
Test suite for Task Planning Agent LangGraph workflow [Member 1]
"""

import pytest
from agents.task_planning.state import TaskPlanningState
from agents.task_planning.parse_order import parse_order
from agents.task_planning.decompose_tasks import decompose_tasks
from agents.task_planning.assign_robot import assign_robot
from agents.task_planning.escalate import escalate_to_human
from agents.task_planning.graph import route_after_assignment


def test_parse_order_node():
    """Verify parse_order node updates state with parsed_order dict."""
    initial_state: TaskPlanningState = {
        "order_raw": "Fetch 2 medical kits from Shelf-A1 to Station-1",
        "parsed_order": None,
        "subtasks": [],
        "assigned_robot_id": None,
        "available_robots": [],
        "requires_escalation": False,
        "escalation_reason": None,
        "status": "INITIALIZED",
        "error_message": None
    }
    
    result = parse_order(initial_state)
    assert "parsed_order" in result
    assert result["status"] == "PARSED"
    assert result["parsed_order"]["order_id"] == "ORD-001"


def test_decompose_tasks_node():
    """Verify decompose_tasks generates subtasks list."""
    state: TaskPlanningState = {
        "order_raw": "Fetch items",
        "parsed_order": {
            "items": [{"sku": "ITEM-1", "quantity": 1, "source": "Shelf-A", "destination": "Pack-1"}]
        },
        "subtasks": [],
        "assigned_robot_id": None,
        "available_robots": [],
        "requires_escalation": False,
        "escalation_reason": None,
        "status": "PARSED",
        "error_message": None
    }
    
    result = decompose_tasks(state)
    assert "subtasks" in result
    assert len(result["subtasks"]) == 2
    assert result["subtasks"][0]["task_type"] == "PICK"
    assert result["subtasks"][1]["task_type"] == "DELIVER"


def test_assign_robot_success():
    """Verify assign_robot selects an IDLE robot with sufficient battery."""
    state: TaskPlanningState = {
        "order_raw": "Fetch items",
        "parsed_order": {},
        "subtasks": [],
        "assigned_robot_id": None,
        "available_robots": [
            {"id": "R1", "status": "BUSY", "battery": 90},
            {"id": "R2", "status": "IDLE", "battery": 75}
        ],
        "requires_escalation": False,
        "escalation_reason": None,
        "status": "DECOMPOSED",
        "error_message": None
    }
    
    result = assign_robot(state)
    assert result["assigned_robot_id"] == "R2"
    assert result["requires_escalation"] is False
    assert route_after_assignment({**state, **result}) == "__end__"


def test_assign_robot_triggers_escalation():
    """Verify assign_robot triggers escalation when all robots are unavailable."""
    state: TaskPlanningState = {
        "order_raw": "Fetch items",
        "parsed_order": {},
        "subtasks": [],
        "assigned_robot_id": None,
        "available_robots": [
            {"id": "R1", "status": "BUSY", "battery": 90},
            {"id": "R2", "status": "IDLE", "battery": 10}  # Low battery < 20%
        ],
        "requires_escalation": False,
        "escalation_reason": None,
        "status": "DECOMPOSED",
        "error_message": None
    }
    
    result = assign_robot(state)
    assert result["assigned_robot_id"] is None
    assert result["requires_escalation"] is True
    assert route_after_assignment({**state, **result}) == "escalate_to_human"
    
    escalate_result = escalate_to_human({**state, **result})
    assert escalate_result["status"] == "ESCALATED"
