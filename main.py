"""
WareFlow AI - Primary Application Gateway & Entry Point [Member 4]
FastAPI server exposing REST endpoints, WebSocket telemetry, security integration,
and inter-agent event bus communication.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Agent & Simulation Imports
from agents.task_planning.graph import build_task_planning_graph
from agents.task_planning.state import TaskPlanningState
from agents.knowledge_compliance.agent import KnowledgeComplianceAgent
from agents.exception_handling.agent import ExceptionHandlingAgent
from simulation.environment import WarehouseEnvironment
from simulation.robot import RobotState

# Communication & Security Imports [Member 4]
from communication import get_event_bus, AgentMessageEnvelope, EventType, MessagePriority, MCPMessage
from security import (
    sanitize_user_input,
    create_access_token,
    verify_token,
    authenticate_user,
    get_current_user
)

logger = logging.getLogger("wareflow.gateway")

# Global instances
event_bus = get_event_bus()
sim_env = WarehouseEnvironment(
    width=int(os.getenv("GRID_WIDTH", 20)),
    height=int(os.getenv("GRID_HEIGHT", 15)),
    num_robots=int(os.getenv("NUM_ROBOTS", 4))
)
compliance_agent = KnowledgeComplianceAgent()
exception_agent = ExceptionHandlingAgent()
task_planning_graph = build_task_planning_graph()

# Active WebSocket clients & execution state
active_telemetry_clients: List[WebSocket] = []
simulation_task: Optional[asyncio.Task] = None
is_emergency_stopped: bool = False


async def telemetry_background_loop():
    """Background task advancing simulation, triggering event bus events, and broadcasting telemetry at 2Hz."""
    global is_emergency_stopped
    tick_rate_hz = float(os.getenv("SIMULATION_TICK_RATE_HZ", 2.0))
    interval = 1.0 / tick_rate_hz if tick_rate_hz > 0 else 0.5
    
    while True:
        try:
            if not is_emergency_stopped:
                anomalies = sim_env.tick(delta_time=interval)
                # If anomalies occur, feed to exception handling agent and publish events
                for anomaly in anomalies:
                    await event_bus.publish(AgentMessageEnvelope(
                        source="simulation",
                        destination="exception_handling",
                        event_type=EventType.ANOMALY_DETECTED,
                        payload=anomaly,
                        priority=MessagePriority.HIGH
                    ))
                    
                    recovery_decision = exception_agent.process_telemetry_event(anomaly)
                    if recovery_decision:
                        await event_bus.publish(AgentMessageEnvelope(
                            source="exception_handling",
                            destination="simulation",
                            event_type=EventType.RECOVERY_ACTION,
                            payload=recovery_decision,
                            priority=MessagePriority.HIGH
                        ))
            
            telemetry = sim_env.get_fleet_telemetry()
            
            # Publish TELEMETRY_UPDATE to EventBus
            await event_bus.publish(AgentMessageEnvelope(
                source="simulation",
                destination="broadcast",
                event_type=EventType.TELEMETRY_UPDATE,
                payload={"fleet_size": len(telemetry), "robots": telemetry},
                priority=MessagePriority.LOW
            ))

            payload = {
                "event_type": EventType.TELEMETRY_UPDATE.value,
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
            logger.error("Error in telemetry_background_loop: %s", e)
            await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global simulation_task
    simulation_task = asyncio.create_task(telemetry_background_loop())
    yield
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

cors_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --- Data Models ---
class OrderDispatchRequest(BaseModel):
    order_text: str = Field(..., example="Fetch 2 medical kits from Shelf-A1 to Station-1")


class AuthLoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="admin123")


class ComplianceCheckRequest(BaseModel):
    payload_weight: float = Field(..., description="Weight of payload in kg", example=15.0)
    speed: float = Field(..., description="Robot speed in m/s", example=1.0)
    is_hazmat: bool = Field(False, description="Flag for hazardous materials")
    target_zone: str = Field("General", description="Target warehouse zone or aisle", example="Zone-A")


class RobotCreateRequest(BaseModel):
    robot_id: str = Field(..., example="R5", description="Unique robot identifier")
    name: Optional[str] = Field(None, example="Warehouse Robot 5")
    model: Optional[str] = Field("AMR", example="AMR")
    capabilities: Optional[List[str]] = Field(["transport", "pallet"], example=["transport", "pallet"])
    initial_position: Optional[List[int]] = Field(None, example=[0, 0])
    battery: Optional[float] = Field(100.0, ge=0.0, le=100.0)


class RobotUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, example="Updated AMR Name")
    capabilities: Optional[List[str]] = Field(None, example=["transport", "pallet", "cold_storage"])
    enabled: Optional[bool] = Field(None)


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


@app.post("/api/v1/auth/login", summary="User authentication & JWT login")
@app.post("/api/v1/auth/token", summary="Issue JWT authentication token")
def login(req: AuthLoginRequest):
    """
    Authenticate demo user credentials ('admin'/'admin123', 'operator'/'operator123')
    and issue a signed Bearer JWT access token.
    """
    auth_user = authenticate_user(req.username, req.password)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(data={"sub": auth_user["username"], "role": auth_user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": auth_user["username"],
        "role": auth_user["role"]
    }


@app.post("/api/v1/orders/dispatch", summary="Dispatch warehouse order")
async def dispatch_order(req: OrderDispatchRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Ingest natural language order, sanitize input against prompt injection, invoke LangGraph task planning agent,
    verify compliance, publish events to event bus, and assign AMR or escalate.
    """
    sanitization_res = sanitize_user_input(req.order_text)
    if not sanitization_res["allowed"]:
        raise HTTPException(status_code=400, detail=sanitization_res["reason"])

    clean_order_text = sanitization_res["sanitized_text"]

    # Publish ORDER_RECEIVED event
    await event_bus.publish(AgentMessageEnvelope(
        source="gateway",
        destination="task_planning",
        event_type=EventType.ORDER_RECEIVED,
        payload={"order_text": clean_order_text, "requested_by": current_user.get("sub")}
    ))

    # Fetch live available robots from simulation
    fleet = sim_env.get_fleet_telemetry()
    available_robots = [
        {"id": r["robot_id"], "battery": r["battery"], "status": r["state"]}
        for r in fleet
    ]
    
    # Construct initial state
    initial_state: TaskPlanningState = {
        "order_text": clean_order_text,
        "order_raw": clean_order_text,
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
    
    # Verify Compliance with KnowledgeComplianceAgent
    comp_check = compliance_agent.check_compliance({
        "payload_weight": 10.0,
        "speed": 1.0,
        "is_hazmat": "hazmat" in clean_order_text.lower(),
        "target_zone": "General"
    })
    
    await event_bus.publish(AgentMessageEnvelope(
        source="gateway",
        destination="knowledge_compliance",
        event_type=EventType.COMPLIANCE_CHECK,
        payload=comp_check
    ))

    if comp_check.get("is_compliant"):
        await event_bus.publish(AgentMessageEnvelope(
            source="knowledge_compliance",
            destination="task_planning",
            event_type=EventType.COMPLIANCE_APPROVED,
            payload=comp_check
        ))
    else:
        await event_bus.publish(AgentMessageEnvelope(
            source="knowledge_compliance",
            destination="task_planning",
            event_type=EventType.COMPLIANCE_REJECTED,
            payload=comp_check
        ))

    if assigned_id:
        await event_bus.publish(AgentMessageEnvelope(
            source="task_planning",
            destination="simulation",
            event_type=EventType.ROBOT_ASSIGNED,
            payload={"robot_id": assigned_id, "order": clean_order_text}
        ))
        await event_bus.publish(AgentMessageEnvelope(
            source="task_planning",
            destination="simulation",
            event_type=EventType.TASK_DISPATCHED,
            payload={"robot_id": assigned_id, "subtasks": result_state.get("subtasks")}
        ))
    elif result_state.get("requires_escalation"):
        await event_bus.publish(AgentMessageEnvelope(
            source="task_planning",
            destination="gateway",
            event_type=EventType.HUMAN_ESCALATION,
            payload={"reason": result_state.get("escalation_reason")},
            priority=MessagePriority.HIGH
        ))

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
def get_fleet_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return live coordinates, battery level, and states for all AMRs."""
    return {
        "timestamp": asyncio.get_event_loop().time(),
        "emergency_stop": is_emergency_stopped,
        "robots": sim_env.get_fleet_telemetry()
    }


@app.get("/api/v1/fleet/robots", summary="List all fleet robots")
def list_fleet_robots():
    """Return array of all registered fleet robots with telemetry & metadata."""
    return {
        "count": len(sim_env.robots),
        "robots": sim_env.get_fleet_telemetry()
    }


@app.post("/api/v1/fleet/robots", summary="Register new robot in fleet")
async def create_robot(req: RobotCreateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Dynamically register a new AMR in the simulation fleet."""
    try:
        new_robot = sim_env.add_robot(
            robot_id=req.robot_id,
            name=req.name,
            model=req.model or "AMR",
            capabilities=req.capabilities,
            initial_position=req.initial_position,
            battery=req.battery if req.battery is not None else 100.0
        )
        
        await event_bus.publish(AgentMessageEnvelope(
            source="gateway",
            destination="broadcast",
            event_type=EventType.ROBOT_ASSIGNED,
            payload={"robot_id": new_robot.robot_id, "action": "ROBOT_CREATED", "operator": current_user.get("sub")}
        ))

        return {
            "success": True,
            "message": f"Robot '{new_robot.robot_id}' registered successfully.",
            "robot": new_robot.to_telemetry()
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@app.get("/api/v1/fleet/robots/{robot_id}", summary="Get single robot details")
def get_robot_detail(robot_id: str):
    """Fetch metadata and live telemetry for a specific AMR."""
    robot = sim_env.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found.")
    return robot.to_telemetry()


@app.patch("/api/v1/fleet/robots/{robot_id}", summary="Update robot metadata")
def update_robot_detail(robot_id: str, req: RobotUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Safely update non-simulation fields (name, capabilities, enabled) of an AMR."""
    try:
        updated = sim_env.update_robot(
            robot_id=robot_id,
            name=req.name,
            capabilities=req.capabilities,
            enabled=req.enabled
        )
        return {
            "success": True,
            "robot": updated.to_telemetry()
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@app.post("/api/v1/fleet/robots/{robot_id}/disable", summary="Disable robot")
async def disable_robot(robot_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Safely disable an AMR from receiving new task assignments."""
    try:
        robot = sim_env.set_robot_enabled(robot_id, enabled=False)
        return {
            "success": True,
            "message": f"Robot '{robot_id}' disabled successfully.",
            "robot": robot.to_telemetry()
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@app.post("/api/v1/fleet/robots/{robot_id}/enable", summary="Enable robot")
async def enable_robot(robot_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Enable a disabled AMR for task assignment."""
    try:
        robot = sim_env.set_robot_enabled(robot_id, enabled=True)
        return {
            "success": True,
            "message": f"Robot '{robot_id}' enabled successfully.",
            "robot": robot.to_telemetry()
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@app.post("/api/v1/simulation/e-stop", summary="Trigger Emergency Stop")
async def trigger_e_stop(resume: bool = Query(False, description="Set true to clear e-stop"), current_user: Dict[str, Any] = Depends(get_current_user)):
    """Global emergency stop trigger halts or resumes AMR movement."""
    global is_emergency_stopped
    is_emergency_stopped = not resume
    for robot in sim_env.robots.values():
        if is_emergency_stopped:
            robot.state = RobotState.ERROR
        elif robot.state == RobotState.ERROR:
            robot.state = RobotState.IDLE
            
    event_type = EventType.SYSTEM_RESUMED if resume else EventType.EMERGENCY_STOP
    await event_bus.publish(AgentMessageEnvelope(
        source="gateway",
        destination="broadcast",
        event_type=event_type,
        payload={"emergency_stopped": is_emergency_stopped, "operator": current_user.get("sub")},
        priority=MessagePriority.CRITICAL
    ))

    return {
        "emergency_stop": is_emergency_stopped,
        "message": "Emergency stop cleared." if resume else "Global emergency stop activated."
    }


@app.post("/api/v1/simulation/resume", summary="Resume fleet movement")
async def resume_simulation(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Resume AMR movement after an emergency stop."""
    return await trigger_e_stop(resume=True, current_user=current_user)


@app.get("/api/v1/compliance/verify", summary="Verify SOP compliance")
async def verify_compliance(
    payload_weight: float = Query(..., description="Weight in kg"),
    speed: float = Query(..., description="Speed in m/s"),
    is_hazmat: bool = Query(False, description="Hazardous material flag"),
    target_zone: str = Query("General", description="Warehouse zone"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Direct query endpoint for SOP and safety compliance validation."""
    params = {
        "payload_weight": payload_weight,
        "speed": speed,
        "is_hazmat": is_hazmat,
        "target_zone": target_zone
    }
    result = compliance_agent.check_compliance(params)
    
    event_type = EventType.COMPLIANCE_APPROVED if result.get("is_compliant") else EventType.COMPLIANCE_REJECTED
    await event_bus.publish(AgentMessageEnvelope(
        source="knowledge_compliance",
        destination="gateway",
        event_type=event_type,
        payload=result
    ))
    return result


@app.get("/api/v1/events/history", summary="Get recent event bus history log")
def get_event_history(limit: int = Query(50, description="Max history logs to return"), current_user: Dict[str, Any] = Depends(get_current_user)):
    """Exposes internal event bus log stream for Member 4 dashboard inspection."""
    return {
        "count": len(event_bus.get_history(limit)),
        "events": [e.model_dump() for e in event_bus.get_history(limit)]
    }


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """Real-time streaming WebSocket delivering 2Hz telemetry ticks."""
    await websocket.accept()
    active_telemetry_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_telemetry_clients:
            active_telemetry_clients.remove(websocket)
    except Exception:
        if websocket in active_telemetry_clients:
            active_telemetry_clients.remove(websocket)


@app.post("/api/v1/mcp/rpc", summary="MCP (Model Context Protocol) JSON-RPC 2.0 Agent Gateway")
async def mcp_rpc_gateway(msg: MCPMessage):
    """
    Model Context Protocol (MCP) HTTP interface allowing agents to execute cross-module tools.
    Supports methods: tools/call, tools/list, agent/dispatch, agent/verify, agent/reroute.
    """
    method = msg.method or ""
    params = msg.params or {}

    if method == "tools/list":
        return MCPMessage(
            id=msg.id,
            result={
                "tools": [
                    {"name": "task_planner.dispatch", "description": "Dispatch natural language order to Task Planner agent"},
                    {"name": "compliance.check", "description": "Verify operation parameters against Qdrant SOP rules"},
                    {"name": "exception.reroute", "description": "Request A* detour reroute for a blocked AMR"},
                    {"name": "fleet.telemetry", "description": "Get current 2D telemetry for all AMRs"}
                ]
            }
        )

    if method in ("tools/call", "agent/dispatch", "task_planner.dispatch"):
        tool_name = params.get("name") or method
        if tool_name in ("task_planner.dispatch", "agent/dispatch"):
            order_text = params.get("arguments", {}).get("order_text") or params.get("order_text", "")
            res = await dispatch_order(OrderDispatchRequest(order_text=order_text), current_user={"sub": "mcp_agent"})
            return MCPMessage(id=msg.id, result=res)

        if tool_name in ("compliance.check", "agent/verify"):
            args = params.get("arguments") or params
            res = compliance_agent.check_compliance(args)
            return MCPMessage(id=msg.id, result=res)

        if tool_name in ("exception.reroute", "agent/reroute"):
            robot_id = params.get("arguments", {}).get("robot_id") or params.get("robot_id")
            goal_x = params.get("arguments", {}).get("goal_x", 0)
            goal_y = params.get("arguments", {}).get("goal_y", 0)
            path = sim_env.reroute_robot(robot_id=robot_id, goal=(goal_x, goal_y))
            return MCPMessage(id=msg.id, result={"robot_id": robot_id, "rerouted_path": path})

        if tool_name in ("fleet.telemetry", "agent/telemetry"):
            return MCPMessage(id=msg.id, result={"robots": sim_env.get_fleet_telemetry()})

    return MCPMessage(
        id=msg.id,
        error={"code": -32601, "message": f"Method or tool '{method}' not recognized"}
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1")
    uvicorn.run("main:app", host=host, port=port, reload=debug)

