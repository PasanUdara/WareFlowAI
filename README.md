# WareFlow AI 🤖📦

> **Autonomous Multi-Agent Coordination System for Warehouse Robot Fleets**  
> *Developed for University Agentic AI Assignment*

---

## 📖 Project Overview

**WareFlow AI** is a distributed multi-agent system designed to orchestrate, monitor, and optimize autonomous mobile robots (AMRs) operating in a modern fulfillment warehouse. The system coordinates order dispatching, dynamically handles anomalies (e.g., deadlocks, battery depletion), and strictly enforces warehouse standard operating procedures (SOPs) via retrieval-augmented generation.

### 🏛️ System Architecture

The system is composed of **3 core specialized agents** and **1 unified integration layer**:

1. **Task Planning Agent (`agents/task_planning/`) — [Member 1]**
   - Built on **LangGraph**.
   - Parses natural language warehouse orders (`parse_order`).
   - Decomposes orders into atomic subtasks (`decompose_tasks`).
   - Checks robot availability and assigns optimal units (`assign_robot`).
   - Employs conditional routing to escalate unresolved tasks to human operators (`escalate_to_human`).

2. **Exception-Handling Agent (`agents/exception_handling/`) — [Member 2]**
   - Monitors live simulated telemetry and anomaly triggers (stalled robots, low battery, path blockages).
   - Dynamically evaluates recovery decisions: rerouting robots via alternate waypoints or escalating severe failures.
   - Couples with the warehouse simulation engine (`simulation/`).

3. **Knowledge & Compliance Agent (`agents/knowledge_compliance/`) — [Member 3]**
   - Implements Retrieval-Augmented Generation (RAG) over warehouse SOPs using **Qdrant**.
   - Validates speed limits, hazardous material handling zones, payload maximums, and battery safety guidelines before task execution.

4. **Integration Layer, Security & Live Dashboard (`communication/`, `security/`, `dashboard/`) — [Member 4]**
   - FastAPI gateway (`main.py`) exposing REST endpoints and WebSocket telemetry feeds.
   - Shared agent messaging protocol (MCP/HTTP-style envelope) and async pub/sub event bus.
   - Security layer featuring JWT-based authentication, password encryption, and prompt injection sanitization.
   - Responsive web dashboard for real-time fleet visualization and order dispatch.

---

## 👥 Contributors & Module Ownership

| Member | Role & Module Ownership | Key Responsibilities |
| :--- | :--- | :--- |
| **Member 1** | **Task Planning Lead** | `agents/task_planning/`<br>LangGraph workflow, StateGraph nodes, TypedDict state, Order decomposer, Planning prompts |
| **Member 2** | **Exception Handling & Simulation Lead** | `agents/exception_handling/`, `simulation/`<br>Telemetry monitor, Rerouter, Anomaly recovery engine, Pygame/Grid simulation |
| **Member 3** | **Knowledge & Compliance Lead** | `agents/knowledge_compliance/`, `data/`<br>Qdrant vector store, SOP document ingestion, RAG retriever, Rule verification |
| **Member 4** | **Integration & Full-Stack Lead** | `communication/`, `security/`, `dashboard/`, `main.py`<br>FastAPI entry point, Inter-agent protocol, JWT auth, Web dashboard |

---

## 🚀 Getting Started (Setup Placeholder)

### 1. Prerequisites
- Python 3.10 or higher
- Git
- (Optional) Docker for containerized Qdrant vector database

### 2. Clone Repository & Setup Environment
```bash
git clone https://github.com/your-org/WareFlowAI.git
cd WareFlowAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in necessary keys:
```bash
cp .env.example .env
```

### 4. Run Application & Services
```bash
# Start FastAPI server & dashboard
python main.py

# In a separate terminal, launch the warehouse simulation
python -m simulation.sim_runner
```

### 5. Run Automated Tests
```bash
pytest
```

---

## 📂 Documentation Directory
- [ARCHITECTURE.md](file:///docs/ARCHITECTURE.md): System architecture diagrams and agent sequence workflows.
- [TECHNICAL.md](file:///docs/TECHNICAL.md): Data schemas, API contracts, and module specifications.
- [ROADMAP.md](file:///docs/ROADMAP.md): Sprint milestones and deliverable tracking per member.
- [CHANGELOG.md](file:///docs/CHANGELOG.md): Version release history and feature change tracking.
