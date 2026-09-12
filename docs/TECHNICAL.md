# WareFlow AI — Technical Specification & Contracts

This document specifies data schemas, interface contracts, state models, and communication protocols for each module.

---

## Task Planning Agent (Member 1)

### State Schema (`TaskPlanningState`)
Defined in `agents/task_planning/state.py`:
- `order_raw`: `str` — Incoming natural language warehouse order.
- `parsed_order`: `dict` — Structured output containing SKU, quantity, source aisle, and target workstation.
- `subtasks`: `list[dict]` — List of decomposed atomic subtasks (`PICK`, `TRANSPORT`, `DELIVER`).
- `assigned_robot_id`: `Optional[str]` — ID of the selected AMR, or `None` if unavailable.
- `requires_escalation`: `bool` — Flag set to true if no suitable robot is available.
- `escalation_reason`: `Optional[str]` — Human-readable rationale for escalation.
- `status`: `str` — Current lifecycle state (`PENDING`, `PLANNED`, `ESCALATED`, `FAILED`).

### LangGraph Workflow Topology
1. `START` -> `parse_order`
2. `parse_order` -> `decompose_tasks`
3. `decompose_tasks` -> `assign_robot`
4. `assign_robot` -> Conditional Router:
   - If `assigned_robot_id is not None` -> `END`
   - If `assigned_robot_id is None` -> `escalate_to_human` -> `END`

---

## Exception-Handling Agent (Member 2)

### Telemetry Event Schema
Received from simulation via `communication/protocol.py`:
- `robot_id`: `str` — Unique identifier of the AMR.
- `event_type`: `str` — `LOW_BATTERY` | `ROBOT_STUCK` | `PATH_BLOCKED` | `MOTOR_STALL`.
- `current_position`: `tuple[int, int]` — Current grid coordinates `(x, y)`.
- `battery_level`: `float` — Remaining battery percentage `(0.0 - 100.0)`.
- `severity`: `str` — `INFO` | `WARNING` | `CRITICAL`.

### Recovery Action Protocol
Returned by `recovery.py`:
- `action_type`: `REROUTE` | `REASSIGN_TASK` | `RETURN_TO_CHARGER` | `ESCALATE_TO_HUMAN`.
- `robot_id`: `str`.
- `waypoints`: `list[tuple[int, int]]` (if rerouting).
- `notes`: `str`.

---

## Knowledge/Compliance Agent (Member 3)

### Qdrant Vector Collection Configuration
- **Collection Name**: `warehouse_sops`
- **Vector Dimension**: `1536` (OpenAI `text-embedding-3-small` / standard embedding model)
- **Distance Metric**: `Cosine`
- **Payload Metadata**:
  - `doc_id`: `str` — Document filename or identifier.
  - `section_title`: `str` — SOP section heading.
  - `category`: `str` — `SAFETY` | `HAZMAT` | `SPEED` | `BATTERY`.
  - `content`: `str` — Markdown text chunk.

### Compliance Validation Interface
Invoked by task planner prior to dispatch:
- **Input**: Proposed task details (payload weight, corridor path, hazmat flag).
- **Evaluation**: Compare proposed parameters against SOP constraints.
- **Output**: `ValidationResult(is_compliant: bool, violations: list[str], citations: list[str])`.

---

## Integration + Dashboard (Member 4)

### Inter-Agent Protocol Envelopes
Defined in `communication/protocol.py` (MCP/HTTP standard):
- `id`: `UUID`
- `source`: `task_planning` | `exception_handling` | `knowledge_compliance` | `simulation` | `gateway`
- `destination`: `all` | `specific_agent`
- `event_type`: `ORDER_RECEIVED` | `TASK_DISPATCHED` | `ANOMALY_DETECTED` | `TELEMETRY_UPDATE`
- `timestamp`: ISO-8601 UTC timestamp
- `payload`: `dict` containing event-specific data
- `signature`: Optional cryptographic token

### REST & WebSocket API Gateway (`main.py`)
- `POST /api/v1/orders/dispatch`: Ingests natural language order and triggers planning graph.
- `GET /api/v1/fleet/status`: Returns current coordinates, battery, and state of all AMRs.
- `POST /api/v1/simulation/e-stop`: Global emergency stop trigger.
- `GET /api/v1/compliance/verify`: Direct test endpoint for SOP queries.
- `WS /ws/telemetry`: Real-time streaming WebSocket delivering 2Hz telemetry ticks.
