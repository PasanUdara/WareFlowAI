"""
Test suite for Exception-Handling Agent [Member 2]
"""

import pytest
from agents.exception_handling.agent import ExceptionHandlingAgent
from agents.exception_handling.logic.monitor import TelemetryMonitor
from agents.exception_handling.logic.recovery import RecoveryEngine


def test_monitor_detects_low_battery():
    monitor = TelemetryMonitor()
    telemetry = {
        "robot_id": "R1",
        "battery": 12.0,  # Below 15% critical threshold
        "state": "MOVING"
    }
    anomaly = monitor.check_for_anomaly(telemetry)
    assert anomaly is not None
    assert anomaly["anomaly_type"] == "LOW_BATTERY"
    assert anomaly["severity"] == "CRITICAL"


def test_monitor_detects_stuck_robot():
    monitor = TelemetryMonitor()
    telemetry = {
        "robot_id": "R2",
        "battery": 80.0,
        "state": "STUCK",
        "stuck_duration": 15.0
    }
    anomaly = monitor.check_for_anomaly(telemetry)
    assert anomaly is not None
    assert anomaly["anomaly_type"] == "ROBOT_STUCK"


def test_recovery_engine_routes_to_charger_on_low_battery():
    engine = RecoveryEngine()
    anomaly = {
        "anomaly_type": "LOW_BATTERY",
        "robot_id": "R1",
        "severity": "CRITICAL"
    }

    action = engine.decide_action(anomaly)

    assert action["action_type"] == "RETURN_TO_CHARGER"
    assert action["robot_id"] == "R1"
    assert action["waypoints"] == []

def test_exception_handling_agent_flow():
    agent = ExceptionHandlingAgent()

    telemetry = {
        "robot_id": "R3",
        "battery": 8.0,
        "state": "MOVING"
    }

    action = agent.process_telemetry_event(telemetry)

    assert action is not None
    assert action["action_type"] == "RETURN_TO_CHARGER"
    assert action["robot_id"] == "R3"
