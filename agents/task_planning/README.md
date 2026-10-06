# Task Planning Agent — WareFlow AI

> **Member 1** — one of 4 agents in the WareFlow AI multi-agent warehouse robot
> coordination system. This module implements order parsing, task decomposition,
> robot assignment, and escalation/clarification workflows using
> **LangGraph + Groq (llama-3.3-70b-versatile)**.

---

## State Schema (`TaskPlanningState`)

| Field              | Type                      | Description                                              |
| ------------------ | ------------------------- | -------------------------------------------------------- |
| `order_text`       | `str`                     | Raw natural-language warehouse order                     |
| `parsed_order`     | `Optional[dict]`          | `{item, quantity, source, destination}` extracted by LLM |
| `subtasks`         | `Optional[List[dict]]`    | Ordered robot actions `{step, action, target, item, qty}`|
| `available_robots` | `Optional[List[str]]`     | Robot IDs available for assignment                       |
| `assigned_robot`   | `Optional[str]`           | ID of the robot selected for the task                    |
| `status`           | `str`                     | Lifecycle status (see below)                             |

### Status Values

`pending` → `parsed` → `decomposed` → `assigned` *(happy path)*

Other terminal states: `parse_failed`, `needs_clarification`, `failed_no_robot`, `escalated`

---

## Node Flow

```
┌─────────────┐
│    START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌────────────────┐
│ parse_order  │────►│ clarify_order  │──► END
│ (Groq LLM)  │fail │ needs_clarif.  │
└──────┬──────┘     └────────────────┘
       │ success
       ▼
┌──────────────────┐
│ decompose_tasks  │
│   (Groq LLM)     │
└──────┬───────────┘
       │
       ▼
┌──────────────┐     ┌─────────────────────┐
│ assign_robot │────►│ escalate_to_human   │──► END
│              │fail │ status="escalated"  │
└──────┬───────┘     └─────────────────────┘
       │ success
       ▼
┌─────────────┐
│     END     │
│ "assigned"  │
└─────────────┘
```

### Nodes (under `/nodes`)

| Node                  | File                   | Purpose                                                  |
| --------------------- | ---------------------- | -------------------------------------------------------- |
| `parse_order`         | `nodes/parse_order.py` | Groq call → structured JSON `{item, qty, src, dest}`     |
| `decompose_tasks`     | `nodes/decompose_tasks.py` | Groq call → ordered action list (navigate/pick/drop) |
| `assign_robot`        | `nodes/assign_robot.py`| Pick a robot from available pool (swappable stub)        |
| `escalate_to_human`   | `nodes/escalate_to_human.py` | Log + set status when no robot available           |
| `clarify_order`       | `nodes/clarify_order.py`     | Log + set status when parsing failed               |

---

## API Endpoint

**`POST /plan-task`** — accepts `{"order_text": "..."}`, returns the full final state.

### Run Standalone

```bash
# 1. Set your Groq API key in .env or environment
export GROQ_API_KEY="your-groq-api-key"

# 2. Install dependencies
pip install -r agents/task_planning/requirements.txt

# 3. Start the standalone API server
uvicorn agents.task_planning.api:router --host 0.0.0.0 --port 8001
```

Or mount the router in the main app (already wired in `main.py`):

```python
from agents.task_planning.api import router
app.include_router(router)
```

### Invoke the Graph Programmatically

```python
from agents.task_planning import build_task_planning_graph, TaskPlanningState

graph = build_task_planning_graph()

result = graph.invoke({
    "order_text": "Move 5 boxes from Shelf-B2 to Station-3",
    "parsed_order": None,
    "subtasks": None,
    "available_robots": ["AMR-01", "AMR-02"],
    "assigned_robot": None,
    "status": "pending",
})
print(result["status"])          # "assigned"
print(result["assigned_robot"])  # "AMR-01"
```

---

## Testing

All unit tests mock the Groq API — no real API calls are made during pytest.

```bash
# From the project root
pytest agents/task_planning/tests/ -v
```

### Test Scenarios

| Test                              | Expected Final Status      |
| --------------------------------- | -------------------------- |
| Valid order + robots available     | `assigned`                 |
| Valid order + no robots            | `escalated`                |
| Malformed LLM response            | `needs_clarification`      |

---

## Configuration

| Env Variable      | Required | Description                                    |
| ----------------- | -------- | ---------------------------------------------- |
| `GROQ_API_KEY`    | ✅       | Groq API key (starts with `gsk_`)              |
| `GROQ_MODEL_NAME` | Optional | Default: `llama-3.3-70b-versatile`             |

> **Security**: The API key is read from an environment variable — never hard-coded.
> Order text is sanitised (stripped, length-capped to 500 chars, control chars removed)
> before being sent to the LLM.

---

## Integration Points

- **Simulation module (Member 3)**: The `query_available_robots()` stub in
  `nodes/assign_robot.py` should be replaced with a live call to
  `WarehouseEnvironment.get_idle_robots()`.
- **Integration layer (Member 4)**: The `main.py` gateway already imports
  `build_task_planning_graph` and invokes it via the `/api/v1/orders/dispatch`
  endpoint.

---

## Folder Structure

```
agents/task_planning/
├── __init__.py          # Package exports
├── state.py             # TaskPlanningState TypedDict
├── graph.py             # LangGraph StateGraph wiring
├── prompts.py           # All LLM prompt templates
├── api.py               # FastAPI router (POST /plan-task)
├── requirements.txt     # Agent-scoped dependencies
├── README.md            # This file
├── nodes/
│   ├── __init__.py
│   ├── parse_order.py
│   ├── decompose_tasks.py
│   ├── assign_robot.py
│   ├── escalate_to_human.py
│   └── clarify_order.py
├── tests/
│   ├── __init__.py
│   └── test_planning_graph.py
├── logic/               # (legacy) helper algorithms
│   ├── __init__.py
│   └── decomposer.py
└── prompts/             # (legacy) old prompt location
    ├── __init__.py
    └── planning_prompts.py
```
