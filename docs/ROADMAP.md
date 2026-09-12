# WareFlow AI — Development Roadmap

This document details upcoming development milestones, sprint goals, and technical deliverables organized by module ownership.

---

## Milestone 1: Core Scaffolding & Interfaces (Sprint 1)
- [x] Scaffolding directory tree, placeholder modules, and test suites.
- [ ] Define standardized Pydantic interfaces across all agents.
- [ ] Establish local simulation and mock service runtime.

---

## Task Planning Agent (Member 1)
- [ ] **Phase 1: Order Ingestion & Parsing**
  - Implement LLM-based order parsing with few-shot prompts in `parse_order.py`.
  - Add regex fallback parser for standard SKU syntax (`PICK <QTY> <ITEM> FROM <BIN>`).
- [ ] **Phase 2: Task Decomposition**
  - Implement `decompose_tasks.py` to break bulk orders into atomic subtasks (`PICK`, `TRANSPORT`, `DELIVER`).
- [ ] **Phase 3: Fleet Allocation & Availability Checks**
  - Query fleet state in `assign_robot.py` based on battery, payload capacity, and location proximity.
- [ ] **Phase 4: Conditional Escalation**
  - Complete LangGraph conditional edge routing to `escalate_to_human.py` when zero robots qualify.
- [ ] **Phase 5: Graph Integration & Unit Tests**
  - Finalize `graph.py` StateGraph and deliver comprehensive test coverage in `tests/test_planning_graph.py`.

---

## Exception-Handling Agent (Member 2)
- [ ] **Phase 1: Telemetry Stream Monitoring**
  - Implement listener in `monitor.py` for simulated anomaly triggers (`BATTERY_CRITICAL`, `ROBOT_STUCK`, `OBSTACLE_DETECTED`).
- [ ] **Phase 2: Recovery Strategy Engine**
  - Build decision logic in `recovery.py` to classify anomaly severity and determine recovery action.
- [ ] **Phase 3: Dynamic Pathfinder / Rerouter**
  - Implement A* grid search in `rerouter.py` to calculate detour waypoints avoiding deadlocks/obstacles.
- [ ] **Phase 4: Warehouse Simulation Engine**
  - Implement 2D grid mechanics (`grid.py`), AMR movement physics (`robot.py`), and tick loop (`environment.py`).
  - Develop fake sensor event generator (`sensor_events.py`) and Pygame visualizer (`sim_runner.py`).

---

## Knowledge/Compliance Agent (Member 3)
- [ ] **Phase 1: SOP Document Ingestion**
  - Implement markdown parser and chunking pipeline in `ingestion.py`.
  - Configure Qdrant vector database collection with appropriate distance metrics.
- [ ] **Phase 2: Semantic RAG Retrieval**
  - Build similarity search engine in `rag_engine.py` to retrieve relevant SOP guidelines given query context.
- [ ] **Phase 3: Compliance & Rule Validation**
  - Implement deterministic safety checks in `rules_checker.py` (speed limits, hazmat restrictions, max payload).
- [ ] **Phase 4: Pre-Execution Order Verification**
  - Expose compliance validation hook for the Task Planning Agent before tasks are dispatched to robots.

---

## Integration + Dashboard (Member 4)
- [ ] **Phase 1: FastAPI Gateway & Endpoints**
  - Implement REST endpoints for order submission, fleet query, and emergency stops.
  - Implement WebSocket endpoint (`/ws/telemetry`) to stream real-time robot positions to the client.
- [ ] **Phase 2: Agent Communication Protocol**
  - Implement MCP/HTTP-style JSON messaging schema and async pub/sub event bus in `communication/`.
- [ ] **Phase 3: Security & Governance**
  - Implement JWT authentication with role-based access control (Operator, Supervisor, Admin).
  - Implement prompt sanitization and prompt injection defense in `security/sanitization.py`.
- [ ] **Phase 4: Interactive Dashboard**
  - Build responsive web dashboard with HTML5 Canvas 2D warehouse map, live telemetry indicators, and order dispatch console.
