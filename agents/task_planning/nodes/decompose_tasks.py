"""
LangGraph Node: decompose_tasks [Member 1]
Calls Groq (llama-3.3-70b-versatile) to break a parsed order into an ordered list of
low-level robot actions (navigate, pick, drop) returned as JSON.
"""

import json
import logging
import os
from typing import Any, Dict

from groq import Groq

from agents.task_planning.prompts import TASK_DECOMPOSE_PROMPT
from agents.task_planning.state import TaskPlanningState

logger = logging.getLogger(__name__)


def decompose_tasks(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Decompose the parsed order into atomic robot actions via Gemini.

    On success  → sets subtasks list and status="decomposed".
    On failure  → falls back to a rule-based decomposition so the pipeline
                  can still proceed.
    """
    parsed_order = state.get("parsed_order") or {}

    parsed_order_json = json.dumps(parsed_order, indent=2)
    prompt = TASK_DECOMPOSE_PROMPT.format(parsed_order_json=parsed_order_json)

    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY environment variable is not set")

        model_name = os.environ.get("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

        raw_text = response.choices[0].message.content.strip()
        parsed_json = json.loads(raw_text)

        # Groq with json_object may wrap the list in an object key like {"steps": [...]} or return list directly
        if isinstance(parsed_json, list):
            subtasks = parsed_json
        elif isinstance(parsed_json, dict):
            # Check if any value is a list of steps
            for key in ["steps", "subtasks", "tasks", "actions"]:
                if key in parsed_json and isinstance(parsed_json[key], list):
                    subtasks = parsed_json[key]
                    break
            else:
                # If single list value in dict
                list_vals = [v for v in parsed_json.values() if isinstance(v, list)]
                if list_vals:
                    subtasks = list_vals[0]
                else:
                    raise ValueError(f"Could not extract steps array from response dict: {parsed_json}")

        # Ensure we got a list
        if not isinstance(subtasks, list):
            raise ValueError(f"Expected a JSON array, got {type(subtasks).__name__}")

        logger.info("Tasks decomposed into %d steps", len(subtasks))
        return {"subtasks": subtasks, "status": "decomposed"}

    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Groq decomposition failed (%s), using rule-based fallback", exc)
    except Exception as exc:
        logger.warning("Unexpected error in decompose_tasks (%s), using fallback", exc)

    # -------------------------------------------------------------------
    # Rule-based fallback: navigate → pick → navigate → drop
    # -------------------------------------------------------------------
    item = parsed_order.get("item", "UNKNOWN")
    qty = parsed_order.get("quantity", 1)
    source = parsed_order.get("source", "UNKNOWN")
    destination = parsed_order.get("destination", "UNKNOWN")

    fallback_subtasks = [
        {"step": 1, "action": "navigate", "target": source, "item": None, "qty": None},
        {"step": 2, "action": "pick", "target": source, "item": item, "qty": qty},
        {"step": 3, "action": "navigate", "target": destination, "item": None, "qty": None},
        {"step": 4, "action": "drop", "target": destination, "item": item, "qty": qty},
    ]

    logger.info("Fallback decomposition produced %d steps", len(fallback_subtasks))
    return {"subtasks": fallback_subtasks, "status": "decomposed"}
