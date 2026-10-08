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
   - Responsive React control center for live fleet visualization, order dispatch, task monitoring, SOP compliance, exception recovery, event history, emergency control, and proposed commercial plans.

---

## 👥 Contributors & Module Ownership

| Member | Role & Module Ownership | Key Responsibilities |
| :--- | :--- | :--- |
| **Member 1** | **Task Planning Lead** | `agents/task_planning/`<br>LangGraph workflow, StateGraph nodes, TypedDict state, Order decomposer, Planning prompts |
| **Member 2** | **Exception Handling & Simulation Lead** | `agents/exception_handling/`, `simulation/`<br>Telemetry monitor, Rerouter, Anomaly recovery engine, Pygame/Grid simulation |
| **Member 3** | **Knowledge & Compliance Lead** | `agents/knowledge_compliance/`, `data/`<br>Qdrant vector store, SOP document ingestion, RAG retriever, Rule verification |
| **Member 4** | **Integration & Full-Stack Lead** | `communication/`, `security/`, `dashboard/`, `main.py`<br>FastAPI entry point, Inter-agent protocol, JWT auth, Web dashboard |

---

## 🚀 Getting Started

### Option A: Running with Docker & Docker Compose (Recommended)

Running with Docker is the quickest and cleanest way to launch the entire WareFlow AI system—including the FastAPI gateway, LangGraph agents, warehouse simulation, and containerized Qdrant vector database—without needing local Python dependencies.

#### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on Windows, macOS, or Linux.
- Ensure **Docker Desktop is started and running** before executing Docker commands.

#### 2. Clone Repository & Navigate
```bash
git clone https://github.com/your-org/WareFlowAI.git
cd WareFlowAI
```

#### 3. Configure Environment Variables
Create a local `.env` file from the provided template:

- **On Linux / macOS / Git Bash:**
  ```bash
  cp .env.example .env
  ```
- **On Windows PowerShell:**
  ```powershell
  Copy-Item .env.example .env
  ```

*(Optional)*: If you want to use live LLM parsing, open `.env` and configure your Groq API key:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL_NAME=openai/gpt-oss-120b
```

#### 4. Build and Start the Services

- **Run Full Stack (Frontend + Backend + Qdrant DB):**
  ```bash
  docker compose up -d --build
  ```
- **Run Backend Only (API Gateway + Qdrant DB):**
  ```bash
  docker compose up -d app qdrant
  ```
- **Run Frontend Only in Docker:**
  ```bash
  docker compose up -d frontend
  ```
- **Run with Live Continuous Simulation Engine:**
  To start the continuous headless warehouse simulation loop alongside all services:
  ```bash
  docker compose --profile full up --build
  ```

#### 5. Verify & Access Dashboards
Once running, the following services and endpoints are immediately available:

| Service / Interface | URL | Description |
| :--- | :--- | :--- |
| **Frontend Web Dashboard** | [http://localhost:5173](http://localhost:5173) | Interactive React + Vite AMR Control Center |
| **FastAPI Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation and testing interface |
| **ReDoc API Reference** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Alternative OpenAPI documentation view |
| **Service Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Real-time health status of agents and simulation |
| **Qdrant Web Console** | [http://localhost:6333/dashboard](http://localhost:6333/dashboard) | Vector database web GUI and collection inspector |
| **Qdrant REST API** | [http://localhost:6333](http://localhost:6333) | Vector DB REST endpoints |
| **WebSocket Telemetry** | `ws://localhost:8000/ws/telemetry` | 2Hz live AMR position and battery stream |

The frontend waits for the API container's health check before starting, which prevents the login proxy from sending requests while backend dependencies and the embedding model are still initializing. The frontend reuses the live fleet, exception, event-history, order-dispatch, compliance, and emergency-control APIs. The backend does not currently expose a durable order/task listing endpoint, so the Tasks view combines robot-reported current assignments with dispatch responses stored only for the current browser session. Commercial pricing and deployment options shown in the UI are proposals for the university project, not actual customer pricing or deployment claims.

#### 6. Test Endpoints via CLI

- **Check Gateway Health:**
  ```bash
  curl http://localhost:8000/health
  ```
- **Dispatch a Warehouse Order:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/orders/dispatch \
    -H "Content-Type: application/json" \
    -d "{\"order_text\": \"Fetch 2 medical kits from Shelf-A1 to Station-1\"}"
  ```
- **Query Fleet Telemetry:**
  ```bash
  curl http://localhost:8000/api/v1/fleet/status
  ```
- **Trigger Emergency Stop (E-Stop):**
  ```bash
  curl -X POST http://localhost:8000/api/v1/simulation/e-stop
  ```
- **Resume After Emergency Stop:**
  ```bash
  curl -X POST "http://localhost:8000/api/v1/simulation/e-stop?resume=true"
  ```
- **Verify SOP Compliance:**
  ```bash
  curl "http://localhost:8000/api/v1/compliance/verify?payload_weight=15.0&speed=1.0&is_hazmat=false&target_zone=General"
  ```

#### 7. Useful Docker Management Commands

- **Stream Container Logs:**
  ```bash
  docker compose logs -f app
  ```
- **Run Automated Tests in Container:**
  ```bash
  docker compose run --rm app pytest
  ```
- **Access Container Shell (Bash):**
  ```bash
  docker compose exec app bash
  ```
- **Stop All Containers:**
  ```bash
  docker compose down
  ```
- **Stop and Reset Database Volume:**
  ```bash
  docker compose down -v
  ```

#### 8. Docker Troubleshooting
- **Error: `error during connect: ... pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`**:
  Docker Desktop is not currently running. Launch **Docker Desktop** from your Applications / Start Menu and wait until the whale icon indicates "Engine Running".
- **Port Conflict (Port 8000 or 6333 already in use)**:
  Ensure no other local process is occupying port `8000` or `6333`, or change the host port mappings in `docker-compose.yml` (e.g. `"8080:8000"`).

---

### Option B: Running Locally (Without Docker)

#### 1. Prerequisites
- Python 3.10 or higher
- Git

#### 2. Create & Activate Virtual Environment
```bash
# Clone and navigate
git clone https://github.com/your-org/WareFlowAI.git
cd WareFlowAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

#### 3. Configure Local Environment
```bash
# On Linux/macOS:
cp .env.example .env
# On Windows PowerShell:
Copy-Item .env.example .env
```
*Note: When running locally without Docker, set `QDRANT_HOST=localhost` in `.env`.*

#### 4. Run Application Gateway & Simulation
In Terminal 1 (Start FastAPI Gateway):
```bash
python main.py
```

In Terminal 2 (Start Warehouse Simulation):
```bash
python -m simulation.sim_runner
```

#### 5. Run Automated Tests
```bash
pytest
```

---

## 📂 Documentation Directory
- [ARCHITECTURE.md](file:///docs/ARCHITECTURE.md): System architecture diagrams and agent sequence workflows.
- [TECHNICAL.md](file:///docs/TECHNICAL.md): Data schemas, API contracts, and module specifications.
- [ROADMAP.md](file:///docs/ROADMAP.md): Sprint milestones and deliverable tracking per member.
- [CHANGELOG.md](file:///docs/CHANGELOG.md): Version release history and feature change tracking.
