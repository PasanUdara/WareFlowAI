"""
Test suite for Knowledge & Compliance Agent [Member 3]
"""

import pytest
from agents.knowledge_compliance.agent import KnowledgeComplianceAgent
from agents.knowledge_compliance.logic.rules_checker import RulesChecker
from agents.knowledge_compliance.logic.rag_engine import RAGEngine


def test_rules_checker_detects_hazmat_speed_violation():
    checker = RulesChecker()
    task = {
        "payload_weight_kg": 20.0,
        "proposed_speed_ms": 1.2,  # Hazmat limit is 0.8 m/s
        "is_hazmat": True
    }
    violations = checker.evaluate(task)
    assert len(violations) > 0
    assert any("Hazmat speed" in v for v in violations)


def test_rules_checker_detects_overweight_payload():
    checker = RulesChecker()
    task = {
        "payload_weight_kg": 150.0,  # Max limit is 100 kg
        "proposed_speed_ms": 1.0,
        "is_hazmat": False
    }
    violations = checker.evaluate(task)
    assert len(violations) > 0
    assert any("Payload 150.0kg exceeds" in v for v in violations)


def test_rules_checker_approves_compliant_task():
    checker = RulesChecker()
    task = {
        "payload_weight_kg": 30.0,
        "proposed_speed_ms": 0.5,
        "is_hazmat": True
    }
    violations = checker.evaluate(task)
    assert len(violations) == 0


def test_rag_engine_mock_search():
    rag = RAGEngine()
    results = rag.search_sops("hazmat speed limits", top_k=2)
    assert len(results) == 2
    assert "section_title" in results[0]
    assert "SOP-HAZ-002" in results[0]["section_title"]


def test_knowledge_compliance_agent_full_check():
    agent = KnowledgeComplianceAgent()
    task = {
        "payload_weight_kg": 40.0,
        "proposed_speed_ms": 1.5,
        "is_hazmat": True,
        "target_zone": "Sector-H"
    }
    result = agent.check_compliance(task)
    assert result["is_compliant"] is False
    assert len(result["violations"]) > 0
    assert len(result["sop_citations"]) > 0
