# WareFlow AI — Changelog

All notable changes to the WareFlow AI project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Task Planning Agent (Member 1)
- Initial scaffold of LangGraph state schema (`TaskPlanningState`).
- Placeholder node stubs: `parse_order`, `decompose_tasks`, `assign_robot`, `escalate_to_human`.
- Initial LangGraph `StateGraph` compilation setup in `graph.py`.
- Prompt templates and decomposer heuristics placeholders.

### Exception-Handling Agent (Member 2)
- Initial scaffold of exception handling loop and recovery decision matrix.
- Telemetry monitor listener placeholder for robot status events.
- Recovery logic stubs (rerouting vs. human escalation).
- Warehouse simulation environment, 2D grid, robot state machine, and fake sensor event generator.

### Knowledge/Compliance Agent (Member 3)
- Initial scaffold of RAG pipeline and Qdrant vector database connector.
- Markdown SOP ingestion and chunking placeholders.
- Rule checker stub for safety constraints (speed, hazmat, battery).
- Standard operating procedure documents added under `data/sop_documents/`.

### Integration + Dashboard (Member 4)
- FastAPI application entry point with REST and WebSocket routing.
- Inter-agent messaging protocol schema (MCP/HTTP envelope) and async event bus.
- Security utilities: JWT token generation/validation, password hashing, and input sanitization.
- Dashboard frontend scaffolding (HTML5, CSS3, JavaScript visualizer).

---

## [0.1.0] - Scaffolding Release
- Initial project directory layout and team member ownership structure established.
- CI pipeline workflow defined in `.github/workflows/ci.yml`.
