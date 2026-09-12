# WareFlow AI — Architecture Overview

## Multi-Agent System Architecture

```mermaid
graph TD
    User([Warehouse Operator / ERP]) -->|Natural Language Order| Gateway[FastAPI Gateway / main.py]
    Gateway -->|Auth & Token Check| Security[Security Layer / JWT]
    Gateway -->|Dispatch Order| Planner[Task Planning Agent - LangGraph]

    subgraph "Member 1: Task Planning Agent"
        Planner --> ParseNode[parse_order node]
        ParseNode --> DecomposeNode[decompose_tasks node]
        DecomposeNode --> AssignNode[assign_robot node]
        AssignNode -->|Robot Available?| CheckRobot{Available?}
        CheckRobot -->|Yes| PlanComplete[Task Execution Plan]
        CheckRobot -->|No| EscalateNode[escalate_to_human node]
    end

    subgraph "Member 3: Knowledge & Compliance Agent"
        PlanComplete -->|Validate Compliance| ComplianceAgent[Knowledge / Compliance Agent]
        ComplianceAgent -->|RAG Vector Query| Qdrant[(Qdrant Vector DB / SOPs)]
        Qdrant -->|SOP Context| ComplianceAgent
    end

    subgraph "Member 4: Communication Layer"
        ComplianceAgent -->|Validated Plan| EventBus[Event Bus / MCP Protocol]
    end

    subgraph "Member 2: Simulation & Exception Handling"
        EventBus -->|Execute Tasks| SimEnv[Warehouse Simulation / Pygame Grid]
        SimEnv -->|Telemetry / Sensor Anomalies| ExceptionAgent[Exception-Handling Agent]
        ExceptionAgent -->|Reroute or Escalate| SimEnv
    end

    SimEnv -->|Real-Time Telemetry| WSGateway[WebSocket Telemetry Feed]
    WSGateway --> Dashboard([Frontend Dashboard - HTML5/Canvas])
```

## Module Separation & Team Boundaries

- **Member 1 (Task Planning Agent)**: Resides strictly in `agents/task_planning/`. Manages order understanding, task decomposition, and robot assignment graph.
- **Member 2 (Exception Handling & Simulation)**: Resides in `agents/exception_handling/` and `simulation/`. Manages real-time robot operations, path recalculation, anomaly responses, and fake sensor generation.
- **Member 3 (Knowledge & Compliance Agent)**: Resides in `agents/knowledge_compliance/` and `data/`. Manages vector embeddings, SOP documents, and safety rule checking.
- **Member 4 (Integration, Security & Dashboard)**: Resides in `communication/`, `security/`, `dashboard/`, and `main.py`. Connects all modules into a functional system.
