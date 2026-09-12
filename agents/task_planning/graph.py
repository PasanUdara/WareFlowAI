"""
LangGraph Workflow Orchestration [Member 1]
Wires together order parsing, task decomposition, robot fleet allocation,
and conditional human escalation using LangGraph StateGraph.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from .state import TaskPlanningState
from .parse_order import parse_order
from .decompose_tasks import decompose_tasks
from .assign_robot import assign_robot
from .escalate import escalate_to_human


def route_after_assignment(state: TaskPlanningState) -> Literal["escalate_to_human", "__end__"]:
    """
    Conditional routing edge evaluator after robot assignment step.
    
    If 'requires_escalation' is True (or no robot was assigned), routes to 'escalate_to_human'.
    Otherwise, marks workflow execution complete by routing to END.
    """
    if state.get("requires_escalation", False) or not state.get("assigned_robot_id"):
        return "escalate_to_human"
    return END


def build_task_planning_graph():
    """
    Constructs and compiles the Task Planning LangGraph StateGraph.
    
    Workflow Topology:
        START -> parse_order -> decompose_tasks -> assign_robot -> [Conditional Edge]
                                                                        ├── (No robot) -> escalate_to_human -> END
                                                                        └── (Assigned) -> END
    """
    workflow = StateGraph(TaskPlanningState)
    
    # Register graph nodes
    workflow.add_node("parse_order", parse_order)
    workflow.add_node("decompose_tasks", decompose_tasks)
    workflow.add_node("assign_robot", assign_robot)
    workflow.add_node("escalate_to_human", escalate_to_human)
    
    # Establish linear edges
    workflow.add_edge(START, "parse_order")
    workflow.add_edge("parse_order", "decompose_tasks")
    workflow.add_edge("decompose_tasks", "assign_robot")
    
    # Establish conditional edge from assign_robot
    workflow.add_conditional_edges(
        "assign_robot",
        route_after_assignment,
        {
            "escalate_to_human": "escalate_to_human",
            END: END
        }
    )
    
    # Terminal edge from escalate_to_human
    workflow.add_edge("escalate_to_human", END)
    
    return workflow.compile()
