"""
WareFlow AI - Primary Application Gateway & Entry Point [Member 4]
FastAPI server exposing REST endpoints, WebSocket telemetry, and agent orchestrators.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Agent & Simulation Imports
from agents.task_planning.graph import build_task_planning_graph
from agents.task_planning.state import TaskPlanningState
from agents.knowledge_compliance.agent import KnowledgeComplianceAgent
from agents.exception_handling.agent import ExceptionHandlingAgent
from simulation.environment import WarehouseEnvironment
from simulation.robot import RobotState

# Global state instances
sim_env = WarehouseEnvironment(
    width=int(os.getenv("GRID_WIDTH", 20)),
    height=int(os.getenv("GRID_HEIGHT", 15)),
    num_robots=int(os.getenv("NUM_ROBOTS", 4))
)
compliance_agent = KnowledgeComplianceAgent()
exception_agent = ExceptionHandlingAgent()
task_planning_graph = build_task_planning_graph()

# Active WebSocket connections for telemetry stream
active_telemetry_clients: List[WebSocket] = []
simulation_task: Optional[asyncio.Task] = None
is_emergency_stopped: bool = False


async def telemetry_background_loop():
    """Background task advancing simulation and broadcasting telemetry at 2Hz."""
    global is_emergency_stopped
    tick_rate_hz = float(os.getenv("SIMULATION_TICK_RATE_HZ", 2.0))
    interval = 1.0 / tick_rate_hz if tick_rate_hz > 0 else 0.5
    
    while True:
        try:
            if not is_emergency_stopped:
                anomalies = sim_env.tick(delta_time=interval)
                # If anomalies occur, feed to exception handling agent and execute recovery
                for anomaly in anomalies:
                    recovery_action = exception_agent.process_telemetry_event(anomaly)
                    if recovery_action:
                        sim_env.execute_recovery(recovery_action)
            
            telemetry = sim_env.get_fleet_telemetry()
            payload = {
                "event_type": "TELEMETRY_TICK",
                "emergency_stopped": is_emergency_stopped,
                "robots": telemetry
            }
            
            # Broadcast to connected WebSocket clients
            disconnected = []
            for client in active_telemetry_clients:
                try:
                    await client.send_json(payload)
                except Exception:
                    disconnected.append(client)
            for d in disconnected:
                if d in active_telemetry_clients:
                    active_telemetry_clients.remove(d)
                    
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global simulation_task
    # Start background telemetry streaming loop
    simulation_task = asyncio.create_task(telemetry_background_loop())
    yield
    # Cancel background task on shutdown
    if simulation_task:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="WareFlow AI API Gateway",
    description="Autonomous Multi-Agent Coordination System for Warehouse Robot Fleets",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local frontend dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Data Models ---
class OrderDispatchRequest(BaseModel):
    order_text: str = Field(..., example="Fetch 2 medical kits from Shelf-A1 to Station-1")


class ComplianceCheckRequest(BaseModel):
    payload_weight: float = Field(..., description="Weight of payload in kg", example=15.0)
    speed: float = Field(..., description="Robot speed in m/s", example=1.0)
    is_hazmat: bool = Field(False, description="Flag for hazardous materials")
    target_zone: str = Field("General", description="Target warehouse zone or aisle", example="Zone-A")


# --- Endpoints ---
@app.get("/", summary="Root API info")
def read_root():
    return {
        "project": "WareFlow AI",
        "description": "Multi-Agent Coordination System for Warehouse AMR Fleets",
        "status": "online",
        "docs_url": "/docs",
        "version": "1.0.0"
    }


@app.get("/health", summary="Service health check")
def health_check():
    """Healthcheck endpoint for Docker health probes."""
    return {
        "status": "healthy",
        "emergency_stop": is_emergency_stopped,
        "fleet_size": len(sim_env.robots),
        "agents": {
            "task_planning": "ready",
            "exception_handling": "ready",
            "knowledge_compliance": "ready"
        }
    }


@app.post("/api/v1/orders/dispatch", summary="Dispatch warehouse order")
def dispatch_order(req: OrderDispatchRequest):
    """
    Ingest natural language order, invoke LangGraph task planning agent,
    decompose tasks, check fleet availability, and assign AMR or escalate.
    """
    # Fetch live available robots from simulation
    fleet = sim_env.get_fleet_telemetry()
    available_robots = [
        {"id": r["robot_id"], "battery": r["battery"], "status": r["state"]}
        for r in fleet
    ]
    
    # Construct initial state
    initial_state: TaskPlanningState = {
        "order_text": req.order_text,
        "order_raw": req.order_text,
        "parsed_order": None,
        "subtasks": [],
        "assigned_robot": None,
        "assigned_robot_id": None,
        "available_robots": available_robots,
        "requires_escalation": False,
        "escalation_reason": None,
        "status": "pending",
        "error_message": None
    }
    
    # Run LangGraph StateGraph
    result_state = task_planning_graph.invoke(initial_state)
    assigned_id = result_state.get("assigned_robot") or result_state.get("assigned_robot_id")
    return {
        "success": True,
        "assigned_robot_id": assigned_id,
        "status": result_state.get("status"),
        "requires_escalation": result_state.get("requires_escalation"),
        "escalation_reason": result_state.get("escalation_reason"),
        "parsed_order": result_state.get("parsed_order"),
        "subtasks": result_state.get("subtasks")
    }


@app.get("/api/v1/fleet/status", summary="Get fleet telemetry")
async def get_fleet_status():
    """Return live coordinates, battery level, and states for all AMRs."""
    return {
        "timestamp": asyncio.get_event_loop().time(),
        "emergency_stop": is_emergency_stopped,
        "robots": sim_env.get_fleet_telemetry()
    }


@app.post("/api/v1/simulation/e-stop", summary="Trigger Emergency Stop")
def trigger_e_stop(resume: bool = Query(False, description="Set true to clear e-stop")):
    """Global emergency stop trigger halts or resumes AMR movement."""
    global is_emergency_stopped
    is_emergency_stopped = not resume
    for robot in sim_env.robots.values():
        if is_emergency_stopped:
            robot.state = RobotState.ERROR
        elif robot.state == RobotState.ERROR:
            robot.state = RobotState.IDLE
            
    return {
        "emergency_stop": is_emergency_stopped,
        "message": "Emergency stop cleared." if resume else "Global emergency stop activated."
    }


@app.get("/api/v1/compliance/verify", summary="Verify SOP compliance")
def verify_compliance(
    payload_weight: float = Query(..., description="Weight in kg"),
    speed: float = Query(..., description="Speed in m/s"),
    is_hazmat: bool = Query(False, description="Hazardous material flag"),
    target_zone: str = Query("General", description="Warehouse zone")
):
    """Direct query endpoint for SOP and safety compliance validation."""
    params = {
        "payload_weight": payload_weight,
        "speed": speed,
        "is_hazmat": is_hazmat,
        "target_zone": target_zone
    }
    result = compliance_agent.check_compliance(params)
    return result


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Real-time streaming WebSocket delivering 2Hz telemetry ticks."""
    await websocket.accept()
    active_telemetry_clients.append(websocket)
    try:
        while True:
            # Keep socket alive and allow client to send commands (e.g., ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_telemetry_clients:
            active_telemetry_clients.remove(websocket)
    except Exception:
        if websocket in active_telemetry_clients:
            active_telemetry_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1")
    uvicorn.run("main:app", host=host, port=port, reload=debug)
