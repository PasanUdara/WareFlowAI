"""
FastAPI Router — Task Planning Agent API [Member 1]
Standalone POST /plan-task endpoint.  Another team member's integration
layer (main.py) can mount this router or call it directly.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.task_planning.graph import build_task_planning_graph
from agents.task_planning.state import TaskPlanningState

router = APIRouter(tags=["Task Planning"])

# Compile the graph once at module level so it is re-used across requests.
_compiled_graph = build_task_planning_graph()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class PlanTaskRequest(BaseModel):
    order_text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        example="Move 5 boxes of surgical gloves from Shelf-B2 to Packing-Station-3",
    )


class PlanTaskResponse(BaseModel):
    order_text: str
    parsed_order: dict | None = None
    subtasks: list | None = None
    available_robots: list | None = None
    assigned_robot: str | None = None
    status: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/plan-task", response_model=PlanTaskResponse, summary="Plan a warehouse task")
def plan_task(req: PlanTaskRequest):
    """
    Accept a natural-language warehouse order, run it through the full
    LangGraph task-planning pipeline, and return the final state.
    """
    initial_state: TaskPlanningState = {
        "order_text": req.order_text,
        "parsed_order": None,
        "subtasks": None,
        "available_robots": None,
        "assigned_robot": None,
        "status": "pending",
    }

    try:
        result = _compiled_graph.invoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {exc}") from exc

    return PlanTaskResponse(**result)
