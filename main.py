"""
WareFlow AI - Primary Application Gateway & Entry Point [Member 4]
FastAPI server exposing REST endpoints, WebSocket telemetry, security integration,
and inter-agent event bus communication.
"""

import os
import re
import time
import asyncio
import logging
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from typing import Dict, Any, Optional, List, Set
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
    register_user,
    verify_google_id_token,
    USERS_DB,
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

# Active Exception Handling Lifecycle tracking for frontend demo
active_exception_lifecycle: Dict[str, Any] = {
    "status": "IDLE",
    "anomaly": None,
    "recovery": None,
    "updated_at": time.time()
}
active_recovering_robots: Set[str] = set()


async def process_anomaly_lifecycle(anomaly: Dict[str, Any]):
    """Execute staged anomaly recovery lifecycle allowing frontend to visibly reflect each state."""
    global active_exception_lifecycle
    robot_id = anomaly.get("robot_id")
    if not robot_id or robot_id in active_recovering_robots:
        return

    active_recovering_robots.add(robot_id)
    try:
        # Step 1: DETECTED
        active_exception_lifecycle["status"] = "DETECTED"
        active_exception_lifecycle["anomaly"] = anomaly
        active_exception_lifecycle["recovery"] = None
        active_exception_lifecycle["updated_at"] = time.time()

        await event_bus.publish(AgentMessageEnvelope(
            source="simulation",
            destination="exception_handling",
            event_type=EventType.ANOMALY_DETECTED,
            payload=anomaly,
            priority=MessagePriority.HIGH
        ))

        # Hold for 1.2s to broadcast anomaly state to UI
        await asyncio.sleep(1.2)

        # Step 2: ANALYZING
        active_exception_lifecycle["status"] = "ANALYZING"
        active_exception_lifecycle["updated_at"] = time.time()

        # Hold for 1.0s to simulate agent reasoning & rule lookup
        await asyncio.sleep(1.0)

        recovery_decision = exception_agent.process_telemetry_event(anomaly)
        if recovery_decision:
            # Step 3: RECOVERING
            active_exception_lifecycle["status"] = "RECOVERING"
            active_exception_lifecycle["recovery"] = recovery_decision
            active_exception_lifecycle["updated_at"] = time.time()

            await event_bus.publish(AgentMessageEnvelope(
                source="exception_handling",
                destination="simulation",
                event_type=EventType.RECOVERY_ACTION,
                payload=recovery_decision,
                priority=MessagePriority.HIGH
            ))
            sim_env.execute_recovery(recovery_decision)
    except Exception as exc:
        logger.error("Error in process_anomaly_lifecycle: %s", exc)
        active_recovering_robots.discard(robot_id)


async def telemetry_background_loop():
    """Background task advancing simulation, triggering event bus events, and broadcasting telemetry at 2Hz."""
    global is_emergency_stopped, active_exception_lifecycle
    tick_rate_hz = float(os.getenv("SIMULATION_TICK_RATE_HZ", 2.0))
    interval = 1.0 / tick_rate_hz if tick_rate_hz > 0 else 0.5
    
    while True:
        try:
            if not is_emergency_stopped:
                anomalies = sim_env.tick(delta_time=interval)
                # If anomalies occur, feed to staged exception handling agent lifecycle
                for anomaly in anomalies:
                    rid = anomaly.get("robot_id")
                    if rid and rid not in active_recovering_robots:
                        asyncio.create_task(process_anomaly_lifecycle(anomaly))

            # Check if recovering robot has reached its target or entered charging/idle
            if active_exception_lifecycle["status"] == "RECOVERING":
                rec = active_exception_lifecycle.get("recovery") or {}
                rec_robot_id = rec.get("robot_id")
                if rec_robot_id:
                    rec_robot = sim_env.get_robot(rec_robot_id)
                    if rec_robot and (
                        rec_robot.state == RobotState.CHARGING
                        or (rec_robot.state == RobotState.IDLE and len(rec_robot.waypoints) == 0)
                    ):
                        active_exception_lifecycle["status"] = "RESOLVED"
                        active_exception_lifecycle["updated_at"] = time.time()
                        active_recovering_robots.discard(rec_robot_id)
            elif active_exception_lifecycle["status"] == "RESOLVED":
                if time.time() - float(active_exception_lifecycle.get("updated_at", 0)) > 6.0:
                    active_exception_lifecycle["status"] = "IDLE"
                    active_exception_lifecycle["anomaly"] = None
                    active_exception_lifecycle["recovery"] = None
                    active_exception_lifecycle["updated_at"] = time.time()
            
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
                "robots": telemetry,
                "active_exception": active_exception_lifecycle,
                "task_queue": sim_env.get_task_queue(),
                "blocked_cells": [list(c) for c in sim_env.grid.blocked_cells],
                "dynamic_blocked_cells": [list(c) for c in sim_env.dynamic_blocked_cells]
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

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,http://localhost:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# --- Data Models ---
class OrderDispatchRequest(BaseModel):
    order_text: str = Field(..., example="Fetch 2 medical kits from Shelf-A1 to Station-1")


class AuthLoginRequest(BaseModel):
    username: str = Field(..., example="name@company.com")
    password: str = Field(..., example="SecurePass123")


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=1)
    full_name: Optional[str] = Field(None, min_length=1, max_length=120)
    company_name: Optional[str] = Field(None, max_length=120)
    terms_accepted: bool = False


class AuthRegisterRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=254, example="new_operator")
    password: str = Field(..., min_length=8, example="StrongPass123")
    confirm_password: str = Field(..., min_length=8)
    email: str = Field(..., example="new.operator@wareflow.ai")
    full_name: str = Field(..., min_length=1, max_length=120, example="New Operator")
    company_name: str = Field(..., min_length=1, max_length=120, example="WareFlow Logistics")
    terms_accepted: bool = Field(..., description="User acceptance of the Terms of Service and Privacy Policy")


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


class AnomalyInjectRequest(BaseModel):
    anomaly_type: str = Field(..., example="stuck", description="Anomaly type: 'stuck', 'low_battery', or 'block_path'")


class ScenarioRunRequest(BaseModel):
    scenario_type: str = Field("all_active", example="all_active", description="Scenario type: 'all_active', 'block_and_reroute', 'battery_drain_handover', or 'full_demo'")
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
    Authenticate registered user credentials
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


@app.post("/api/v1/auth/google", summary="Authenticate with Google")
def google_login(req: GoogleAuthRequest):
    """Verify a Google ID token and authenticate or register its verified account."""
    try:
        google_user = verify_google_id_token(req.credential)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_record = next(
        (
            user
            for user in USERS_DB.values()
            if user.get("email", "").lower() == google_user["email"]
        ),
        None,
    )
    if not user_record:
        if req.full_name is None and req.company_name is None and not req.terms_accepted:
            return {
                "requires_registration": True,
                "email": google_user["email"],
                "full_name": str(google_user.get("name", "")).strip(),
            }

        try:
            user_record = register_user(
                username=google_user["email"],
                password=secrets.token_urlsafe(48),
                email=google_user["email"],
                full_name=req.full_name or str(google_user.get("name", "")).strip(),
                role="operator",
                company_name=req.company_name,
                terms_accepted=req.terms_accepted,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    token = create_access_token(data={
        "sub": user_record["username"],
        "role": user_record["role"],
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user_record["username"],
        "role": user_record["role"],
    }


@app.post("/api/v1/auth/register", summary="Register a new WareFlow user")
def register(req: AuthRegisterRequest):
    """Create a new operator account and issue a JWT."""
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation do not match.",
        )

    try:
        user_record = register_user(
            username=req.username,
            password=req.password,
            email=req.email,
            full_name=req.full_name,
            role="operator",
            company_name=req.company_name,
            terms_accepted=req.terms_accepted,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    token = create_access_token(data={"sub": user_record["username"], "role": user_record["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user_record["username"],
        "role": user_record["role"],
        "email": user_record.get("email"),
        "full_name": user_record.get("full_name"),
        "company_name": user_record.get("company_name"),
    }


@app.post("/api/v1/orders/dispatch", summary="Dispatch warehouse order")
async def dispatch_order(
    req: OrderDispatchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    End-to-end warehouse order workflow:

    1. Sanitize user order.
    2. Send order to Task Planning Agent.
    3. Build compliance context from the planned task and live robot telemetry.
    4. Send task to Knowledge/Compliance Agent.
    5. Stop the task if compliance is rejected.
    6. Dispatch the robot only after compliance approval.
    7. Exception Handling Agent continues to process robot telemetry
       through the existing simulation lifecycle.
    """

    # ---------------------------------------------------------------
    # 1. Security / input sanitization
    # ---------------------------------------------------------------
    sanitization_res = sanitize_user_input(req.order_text)

    if not sanitization_res["allowed"]:
        raise HTTPException(
            status_code=400,
            detail=sanitization_res["reason"]
        )

    clean_order_text = sanitization_res["sanitized_text"]

    # ---------------------------------------------------------------
    # 2. Notify Task Planning Agent
    # ---------------------------------------------------------------
    await event_bus.publish(
        AgentMessageEnvelope(
            source="gateway",
            destination="task_planning",
            event_type=EventType.ORDER_RECEIVED,
            payload={
                "order_text": clean_order_text,
                "requested_by": current_user.get("sub")
            }
        )
    )

    # ---------------------------------------------------------------
    # 3. Get live robot information from simulation
    # ---------------------------------------------------------------
    # 3. Get live robot information from simulation
    # ---------------------------------------------------------------
    fleet = sim_env.get_fleet_telemetry()

    # Pre-parse order using fast rule-based parser to identify the pickup source location accurately
    from agents.task_planning.nodes.parse_order import _rule_based_parse_order
    pre_parsed = _rule_based_parse_order(clean_order_text)
    pre_source = (pre_parsed.get("source") if pre_parsed else None)
    if not pre_source:
        m_from = re.search(r"\bfrom\s+(.*?)(?:\s+to\s+|$)", clean_order_text, re.IGNORECASE)
        pre_source = m_from.group(1).strip() if m_from else clean_order_text

    source_pos = sim_env.resolve_location(pre_source)

    # Filter fleet to eligible AMRs with healthy battery (> 20%)
    # Robots in IDLE state or CHARGING state with healthy battery (> 20%) are available
    available_fleet = [
        r for r in fleet
        if r.get("enabled", True)
        and str(r.get("state", "")).lower() in ("idle", "charging")
        and not r.get("waypoints", [])
        and float(r.get("battery", 100)) > 20.0
    ]

    # Sort available robots by distance to the source location (nearest robot first, higher battery tie-breaker)
    if source_pos and available_fleet:
        available_fleet.sort(
            key=lambda r: (
                abs(r["position"][0] - source_pos[0]) + abs(r["position"][1] - source_pos[1]),
                -float(r.get("battery", 100))
            )
        )

    # If any available robots exist, pass them into task planner; otherwise pass empty list to trigger queuing
    available_robots = [
        {
            "id": r["robot_id"],
            "battery": r["battery"],
            "status": r["state"],
            "position": r["position"]
        }
        for r in available_fleet
    ]

    # ---------------------------------------------------------------
    # 4. Run Task Planning Agent
    # ---------------------------------------------------------------
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

    result_state = task_planning_graph.invoke(initial_state)

    assigned_id = (
        result_state.get("assigned_robot")
        or result_state.get("assigned_robot_id")
    )

    parsed = result_state.get("parsed_order") or {}

    # Final verification: guarantee assigned_id is the closest eligible AMR to the finalized parsed source
    real_src = parsed.get("source")
    if real_src:
        real_src_pos = sim_env.resolve_location(real_src)
        if real_src_pos and available_fleet:
            closest_robot = min(
                available_fleet,
                key=lambda r: (
                    abs(r["position"][0] - real_src_pos[0]) + abs(r["position"][1] - real_src_pos[1]),
                    -float(r.get("battery", 100))
                )
            )
            dist = abs(closest_robot["position"][0] - real_src_pos[0]) + abs(closest_robot["position"][1] - real_src_pos[1])
            logger.info(
                "Prioritizing closest robot %s at %s (distance=%d from source '%s' at %s, battery=%.1f%%)",
                closest_robot["robot_id"], closest_robot["position"], dist, real_src, real_src_pos, closest_robot["battery"]
            )
            assigned_id = closest_robot["robot_id"]

    # ---------------------------------------------------------------
    # 5. Handle Task Planning failure or Fleet Overflow (Task Queue)
    # ---------------------------------------------------------------
    if not assigned_id:
        if result_state.get("requires_escalation"):
            await event_bus.publish(
                AgentMessageEnvelope(
                    source="task_planning",
                    destination="gateway",
                    event_type=EventType.HUMAN_ESCALATION,
                    payload={
                        "reason": result_state.get("escalation_reason")
                    },
                    priority=MessagePriority.HIGH
                )
            )
            return {
                "success": False,
                "assigned_robot_id": None,
                "status": "escalated",
                "requires_escalation": True,
                "escalation_reason": result_state.get("escalation_reason"),
                "parsed_order": parsed,
                "subtasks": result_state.get("subtasks") or [],
                "message": f"Order requires human escalation: {result_state.get('escalation_reason')}"
            }

        # If all fleet robots are currently active, enqueue the order
        src_name = parsed.get("source") or "Shelf A2"
        dst_name = parsed.get("destination") or "Packing Station 3"
        item_name = parsed.get("item") or "pallets"
        qty_num = parsed.get("quantity") or 1

        queue_item = {
            "order_id": f"ORD-{int(time.time() * 1000) % 1000000}",
            "order_text": clean_order_text,
            "source_name": src_name,
            "destination_name": dst_name,
            "item": item_name,
            "qty": qty_num,
            "parsed_order": parsed,
            "subtasks": result_state.get("subtasks") or [],
            "queued_at": time.time()
        }
        queue_pos = sim_env.queue_order(queue_item)

        await event_bus.publish(
            AgentMessageEnvelope(
                source="task_planning",
                destination="gateway",
                event_type=EventType.ROBOT_ASSIGNED,
                payload={
                    "status": "queued",
                    "queue_position": queue_pos,
                    "order": queue_item
                },
                priority=MessagePriority.NORMAL
            )
        )

        return {
            "success": True,
            "status": "queued",
            "queue_position": queue_pos,
            "assigned_robot_id": None,
            "requires_escalation": False,
            "escalation_reason": None,
            "parsed_order": parsed,
            "subtasks": result_state.get("subtasks") or [],
            "compliance": {
                "is_compliant": True,
                "violations": [],
                "sop_citations": ["1. Speed Guidelines"]
            },
            "message": f"All robots in the fleet are currently active. Order added to task queue (Position #{queue_pos}). It will automatically dispatch to the nearest AMR upon task completion."
        }

    # ---------------------------------------------------------------
    # 6. Find selected robot's LIVE telemetry
    # ---------------------------------------------------------------
    selected_robot = next(
        (
            robot
            for robot in fleet
            if robot.get("robot_id") == assigned_id
        ),
        None
    )

    if selected_robot is None:
        return {
            "success": False,
            "assigned_robot_id": assigned_id,
            "status": "robot_not_found",
            "parsed_order": parsed,
            "subtasks": result_state.get("subtasks") or [],
            "message": "Assigned robot could not be found in live fleet telemetry."
        }

    # ---------------------------------------------------------------
    # 7. Build Compliance context
    #
    # Member 1's parsed order structure remains unchanged:
    # item / quantity / source / destination
    #
    # Additional runtime information is created here in the
    # integration layer instead of changing Member 1's agent.
    # ---------------------------------------------------------------

    target_zone = parsed.get("destination") or "General"

    is_hazmat = (
        "hazmat" in clean_order_text.lower()
        or "hazardous" in clean_order_text.lower()
        or "chemical" in clean_order_text.lower()
    )

    live_battery = selected_robot.get("battery", 100.0)

    # The current OrderDispatchRequest does not contain payload weight
    # or requested speed. These are integration defaults until such
    # information is provided by the order/catalog system.
    payload_weight = 0.0
    proposed_speed = 1.0

    compliance_params = {
        "payload_weight": payload_weight,
        "speed": proposed_speed,
        "is_hazmat": is_hazmat,
        "target_zone": target_zone,
        "battery_level": live_battery
    }

    # ---------------------------------------------------------------
    # 8. Knowledge & Compliance Agent
    # ---------------------------------------------------------------
    comp_check = compliance_agent.check_compliance(
        compliance_params
    )

    await event_bus.publish(
        AgentMessageEnvelope(
            source="gateway",
            destination="knowledge_compliance",
            event_type=EventType.COMPLIANCE_CHECK,
            payload={
                "task": parsed,
                "robot_id": assigned_id,
                "compliance_parameters": compliance_params,
                "result": comp_check
            }
        )
    )

    # ---------------------------------------------------------------
    # 9. COMPLIANCE GATE
    # ---------------------------------------------------------------
    if not comp_check.get("is_compliant", False):

        await event_bus.publish(
            AgentMessageEnvelope(
                source="knowledge_compliance",
                destination="task_planning",
                event_type=EventType.COMPLIANCE_REJECTED,
                payload=comp_check
            )
        )

        # IMPORTANT:
        # Do NOT dispatch the robot when compliance fails.
        return {
            "success": False,
            "assigned_robot_id": assigned_id,
            "status": "compliance_rejected",
            "requires_escalation": False,
            "parsed_order": parsed,
            "subtasks": result_state.get("subtasks") or [],
            "compliance": comp_check,
            "message": "Task rejected by Knowledge & Compliance Agent. Robot was not dispatched."
        }

    # ---------------------------------------------------------------
    # 10. Compliance approved
    # ---------------------------------------------------------------
    await event_bus.publish(
        AgentMessageEnvelope(
            source="knowledge_compliance",
            destination="task_planning",
            event_type=EventType.COMPLIANCE_APPROVED,
            payload=comp_check
        )
    )

    # ---------------------------------------------------------------
    # 11. Dispatch approved task to robot
    # ---------------------------------------------------------------
    parsed_item = parsed.get("item", "")
    parsed_qty = parsed.get("quantity", "")
    item_str = f"{parsed_qty} {parsed_item}".strip() if (parsed_item or parsed_qty) else "pallets"

    sim_env.dispatch_order_to_robot(
        robot_id=assigned_id,
        source_name=parsed.get("source"),
        destination_name=parsed.get("destination"),
        task_description=clean_order_text,
        item=item_str,
        sub_orders=parsed.get("sub_orders")
    )

    await event_bus.publish(
        AgentMessageEnvelope(
            source="task_planning",
            destination="simulation",
            event_type=EventType.ROBOT_ASSIGNED,
            payload={
                "robot_id": assigned_id,
                "order": clean_order_text
            }
        )
    )

    await event_bus.publish(
        AgentMessageEnvelope(
            source="task_planning",
            destination="simulation",
            event_type=EventType.TASK_DISPATCHED,
            payload={
                "robot_id": assigned_id,
                "subtasks": result_state.get("subtasks") or [],
                "compliance": comp_check
            }
        )
    )

    # ---------------------------------------------------------------
    # 12. Final response
    #
    # Exception Handling Agent is already connected to the telemetry
    # lifecycle in main.py. Once the robot starts moving, telemetry
    # anomalies are processed by ExceptionHandlingAgent.
    # ---------------------------------------------------------------
    return {
        "success": True,
        "assigned_robot_id": assigned_id,
        "status": "dispatched",
        "requires_escalation": result_state.get(
            "requires_escalation",
            False
        ),
        "escalation_reason": result_state.get(
            "escalation_reason"
        ),
        "parsed_order": parsed,
        "subtasks": result_state.get("subtasks") or [],
        "compliance": comp_check,
        "message": (
            "Task planned, compliance approved, "
            "and robot dispatched successfully."
        )
    }


@app.get("/api/v1/fleet/status", summary="Get fleet telemetry")
def get_fleet_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return live coordinates, battery level, and states for all AMRs."""
    return {
        "timestamp": time.time(),
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


@app.post("/api/v1/simulation/robots/{robot_id}/inject-anomaly", summary="Inject synthetic anomaly into AMR for testing")
async def inject_robot_anomaly(
    robot_id: str,
    req: AnomalyInjectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Manually inject an anomaly condition into an AMR to test Exception Handling flow.
    Does NOT bypass the Exception Handling Agent: the simulation loop will detect
    the condition on the next tick and execute the normal agent recovery pipeline.
    """
    try:
        active_recovering_robots.discard(robot_id)
        res = sim_env.inject_anomaly(robot_id, req.anomaly_type)
        return {
            "success": True,
            "message": f"Anomaly '{req.anomaly_type}' successfully injected into robot '{robot_id}'.",
            "details": res
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@app.post("/api/v1/simulation/obstacles/clear", summary="Clear dynamically added obstacles")
async def clear_dynamic_obstacles(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Reset dynamic obstacles back to default grid layout."""
    sim_env.clear_dynamic_obstacles()
    active_recovering_robots.clear()
    return {"success": True, "message": "Dynamic obstacles cleared."}


@app.post("/api/v1/simulation/scenarios/run", summary="Trigger dynamic simulation demo scenarios")
async def run_simulation_scenario(
    req: ScenarioRunRequest = ScenarioRunRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Trigger orchestrated full-fleet demonstration scenarios.
    Supports:
    - 'all_active': Dispatches tasks to all fleet robots simultaneously.
    - 'block_and_reroute': Injects dynamic path blockage and executes A* detour recovery.
    - 'battery_drain_handover': Drains battery, returns AMR to charging bay, hands over in-flight task to another AMR.
    - 'full_demo': End-to-end multi-agent showcase executing all scenarios together.
    """
    try:
        active_recovering_robots.clear()
        res = sim_env.run_mock_scenario(req.scenario_type)
        return {
            "success": True,
            "scenario": req.scenario_type,
            "details": res
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@app.get("/api/v1/simulation/exceptions/active", summary="Get active exception lifecycle state")
def get_active_exception():
    """Return latest exception lifecycle status and dynamic blocked cells."""
    return {
        "lifecycle": active_exception_lifecycle,
        "blocked_cells": [list(c) for c in sim_env.grid.blocked_cells],
        "dynamic_blocked_cells": [list(c) for c in sim_env.dynamic_blocked_cells]
    }
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


@app.get("/api/v1/orders/queue", summary="Get pending queued warehouse orders")
def get_order_queue(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns the list of orders currently waiting in queue for an idle AMR."""
    queue = sim_env.get_task_queue()
    return {
        "count": len(queue),
        "queue": queue
    }


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
