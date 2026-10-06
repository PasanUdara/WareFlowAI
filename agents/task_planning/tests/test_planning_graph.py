"""
Test suite for Task Planning Agent [Member 1]
All Gemini API calls are mocked — tests never hit the real API.
Covers:
  1. Valid order  → status "assigned"
  2. No robots    → status "escalated"
  3. Malformed LLM response → status "needs_clarification"
  4. Individual node unit tests
  5. Routing logic unit tests
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents.task_planning.state import TaskPlanningState
from agents.task_planning.graph import (
    build_task_planning_graph,
    route_after_assign,
    route_after_parse,
)
from agents.task_planning.nodes.parse_order import parse_order, _sanitize_order_text
from agents.task_planning.nodes.decompose_tasks import decompose_tasks
from agents.task_planning.nodes.assign_robot import assign_robot, query_available_robots
from agents.task_planning.nodes.escalate_to_human import escalate_to_human
from agents.task_planning.nodes.clarify_order import clarify_order


# ============================================================================
# Helpers
# ============================================================================
def _base_state(**overrides) -> TaskPlanningState:
    """Return a minimal valid initial state with optional overrides."""
    state: TaskPlanningState = {
        "order_text": "Move 3 crates from Shelf-A1 to Station-2",
        "parsed_order": None,
        "subtasks": None,
        "available_robots": None,
        "assigned_robot": None,
        "status": "pending",
    }
    state.update(overrides)
    return state


def _mock_groq_response(text: str):
    """Create a mock that looks like a Groq chat completion response."""
    choice = MagicMock()
    choice.message.content = text
    response = MagicMock()
    response.choices = [choice]
    return response


# ============================================================================
# Unit tests — individual nodes
# ============================================================================
class TestParseOrder:
    """Tests for the parse_order node."""

    @patch("agents.task_planning.nodes.parse_order.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_successful_parse(self, mock_groq_class):
        """Valid Groq JSON → status='parsed'."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({
                "item": "crates",
                "quantity": 3,
                "source": "Shelf-A1",
                "destination": "Station-2",
            })
        )

        result = parse_order(_base_state())

        assert result["status"] == "parsed"
        assert result["parsed_order"]["item"] == "crates"
        assert result["parsed_order"]["quantity"] == 3

    @patch("agents.task_planning.nodes.parse_order.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_malformed_json(self, mock_groq_class):
        """Groq returns invalid JSON → status='parse_failed'."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            "this is not json at all"
        )

        result = parse_order(_base_state())

        assert result["status"] == "parse_failed"
        assert result["parsed_order"] is None

    @patch("agents.task_planning.nodes.parse_order.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_missing_keys(self, mock_groq_class):
        """Groq returns JSON but missing required keys → status='parse_failed'."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"item": "boxes"})  # missing quantity, source, destination
        )

        result = parse_order(_base_state())

        assert result["status"] == "parse_failed"

    def test_empty_order_text(self):
        """Empty order_text → status='parse_failed' without calling Groq."""
        result = parse_order(_base_state(order_text=""))
        assert result["status"] == "parse_failed"

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key(self):
        """No GROQ_API_KEY env var → status='parse_failed' gracefully."""
        result = parse_order(_base_state())
        assert result["status"] == "parse_failed"


class TestSanitizeOrderText:
    """Tests for input sanitisation."""

    def test_strips_whitespace(self):
        assert _sanitize_order_text("  hello  ") == "hello"

    def test_caps_length(self):
        long_text = "a" * 1000
        assert len(_sanitize_order_text(long_text)) == 500

    def test_removes_control_chars(self):
        assert _sanitize_order_text("hello\x00world") == "helloworld"


class TestDecomposeTasks:
    """Tests for the decompose_tasks node."""

    @patch("agents.task_planning.nodes.decompose_tasks.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_successful_decomposition(self, mock_groq_class):
        """Valid decomposition JSON from Groq."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        subtasks = [
            {"step": 1, "action": "navigate", "target": "Shelf-A1", "item": None, "qty": None},
            {"step": 2, "action": "pick", "target": "Shelf-A1", "item": "crates", "qty": 3},
            {"step": 3, "action": "navigate", "target": "Station-2", "item": None, "qty": None},
            {"step": 4, "action": "drop", "target": "Station-2", "item": "crates", "qty": 3},
        ]
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"steps": subtasks})
        )

        state = _base_state(
            parsed_order={"item": "crates", "quantity": 3, "source": "Shelf-A1", "destination": "Station-2"},
            status="parsed",
        )
        result = decompose_tasks(state)

        assert result["status"] == "decomposed"
        assert len(result["subtasks"]) == 4

    @patch("agents.task_planning.nodes.decompose_tasks.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_fallback_on_bad_json(self, mock_groq_class):
        """Malformed Groq response triggers rule-based fallback."""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response("NOT JSON")

        state = _base_state(
            parsed_order={"item": "crates", "quantity": 3, "source": "Shelf-A1", "destination": "Station-2"},
        )
        result = decompose_tasks(state)

        assert result["status"] == "decomposed"
        assert len(result["subtasks"]) == 4
        assert result["subtasks"][0]["action"] == "navigate"


class TestAssignRobot:
    """Tests for the assign_robot node."""

    def test_assigns_first_available(self):
        """Robots available → picks first, status='assigned'."""
        state = _base_state(available_robots=["R-01", "R-02"])
        result = assign_robot(state)

        assert result["status"] == "assigned"
        assert result["assigned_robot"] == "R-01"

    def test_no_robots_available(self):
        """Empty robot list → status='failed_no_robot'."""
        state = _base_state(available_robots=[])
        result = assign_robot(state)

        assert result["status"] == "failed_no_robot"
        assert result["assigned_robot"] is None

    def test_falls_back_to_stub(self):
        """No available_robots in state → uses query_available_robots stub."""
        state = _base_state(available_robots=None)
        result = assign_robot(state)

        # Stub returns 3 mock robots
        assert result["status"] == "assigned"
        assert result["assigned_robot"] is not None

    def test_stub_returns_list(self):
        """The mock stub itself should return a non-empty list."""
        robots = query_available_robots()
        assert isinstance(robots, list)
        assert len(robots) > 0


class TestEscalateToHuman:
    """Tests for the escalate_to_human node."""

    def test_sets_escalated_status(self):
        result = escalate_to_human(_base_state())
        assert result["status"] == "escalated"


class TestClarifyOrder:
    """Tests for the clarify_order node."""

    def test_sets_needs_clarification(self):
        result = clarify_order(_base_state())
        assert result["status"] == "needs_clarification"


# ============================================================================
# Unit tests — routing functions
# ============================================================================
class TestRouting:
    """Tests for conditional routing logic."""

    def test_route_after_parse_success(self):
        assert route_after_parse(_base_state(status="parsed")) == "decompose_tasks"

    def test_route_after_parse_failure(self):
        assert route_after_parse(_base_state(status="parse_failed")) == "clarify_order"

    def test_route_after_assign_success(self):
        assert route_after_assign(_base_state(status="assigned")) == "__end__"

    def test_route_after_assign_no_robot(self):
        assert route_after_assign(_base_state(status="failed_no_robot")) == "escalate_to_human"


# ============================================================================
# Integration tests — full graph execution (all LLM calls mocked)
# ============================================================================
class TestFullGraph:
    """End-to-end graph invocation tests with mocked Groq."""

    @patch("agents.task_planning.nodes.decompose_tasks.Groq")
    @patch("agents.task_planning.nodes.parse_order.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_happy_path_assigned(self, mock_parse_groq, mock_decompose_groq):
        """Valid order with available robots → final status 'assigned'."""
        # Mock parse_order Groq call
        mock_parse_client = MagicMock()
        mock_parse_groq.return_value = mock_parse_client
        mock_parse_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({
                "item": "surgical gloves",
                "quantity": 5,
                "source": "Shelf-B2",
                "destination": "Packing-Station-3",
            })
        )

        # Mock decompose_tasks Groq call
        mock_decompose_client = MagicMock()
        mock_decompose_groq.return_value = mock_decompose_client
        mock_decompose_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({
                "steps": [
                    {"step": 1, "action": "navigate", "target": "Shelf-B2", "item": None, "qty": None},
                    {"step": 2, "action": "pick", "target": "Shelf-B2", "item": "surgical gloves", "qty": 5},
                    {"step": 3, "action": "navigate", "target": "Packing-Station-3", "item": None, "qty": None},
                    {"step": 4, "action": "drop", "target": "Packing-Station-3", "item": "surgical gloves", "qty": 5},
                ]
            })
        )

        graph = build_task_planning_graph()
        initial: TaskPlanningState = {
            "order_text": "Move 5 boxes of surgical gloves from Shelf-B2 to Packing-Station-3",
            "parsed_order": None,
            "subtasks": None,
            "available_robots": ["AMR-01", "AMR-02"],
            "assigned_robot": None,
            "status": "pending",
        }

        result = graph.invoke(initial)

        assert result["status"] == "assigned"
        assert result["assigned_robot"] == "AMR-01"
        assert result["parsed_order"]["item"] == "surgical gloves"
        assert len(result["subtasks"]) == 4

    @patch("agents.task_planning.nodes.decompose_tasks.Groq")
    @patch("agents.task_planning.nodes.parse_order.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_no_robots_escalated(self, mock_parse_groq, mock_decompose_groq):
        """Valid order but no robots → final status 'escalated'."""
        mock_parse_client = MagicMock()
        mock_parse_groq.return_value = mock_parse_client
        mock_parse_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({
                "item": "crates",
                "quantity": 3,
                "source": "Shelf-A1",
                "destination": "Station-2",
            })
        )

        mock_decompose_client = MagicMock()
        mock_decompose_groq.return_value = mock_decompose_client
        mock_decompose_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({
                "steps": [
                    {"step": 1, "action": "navigate", "target": "Shelf-A1", "item": None, "qty": None},
                    {"step": 2, "action": "pick", "target": "Shelf-A1", "item": "crates", "qty": 3},
                ]
            })
        )

        graph = build_task_planning_graph()
        initial: TaskPlanningState = {
            "order_text": "Move 3 crates from Shelf-A1 to Station-2",
            "parsed_order": None,
            "subtasks": None,
            "available_robots": [],  # ← no robots
            "assigned_robot": None,
            "status": "pending",
        }

        result = graph.invoke(initial)

        assert result["status"] == "escalated"
        assert result["assigned_robot"] is None

    @patch("agents.task_planning.nodes.parse_order.Groq")
    @patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
    def test_malformed_llm_response_needs_clarification(self, mock_groq):
        """Groq returns garbage → parse fails → status 'needs_clarification'."""
        mock_client = MagicMock()
        mock_groq.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            "I cannot understand this order"
        )

        graph = build_task_planning_graph()
        initial: TaskPlanningState = {
            "order_text": "asdfghjkl gibberish order",
            "parsed_order": None,
            "subtasks": None,
            "available_robots": ["AMR-01"],
            "assigned_robot": None,
            "status": "pending",
        }

        result = graph.invoke(initial)

        assert result["status"] == "needs_clarification"
        assert result["parsed_order"] is None
