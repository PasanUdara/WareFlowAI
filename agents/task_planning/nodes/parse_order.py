"""
LangGraph Node: parse_order [Member 1]
Calls Groq (llama-3.3-70b-versatile) with structured JSON output to extract
{item, quantity, source, destination} from a natural-language warehouse order.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional

from groq import Groq

from agents.task_planning.prompts import ORDER_PARSE_PROMPT
from agents.task_planning.state import TaskPlanningState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Input sanitisation — basic defence against prompt injection
# ---------------------------------------------------------------------------
MAX_ORDER_TEXT_LENGTH = 500


def _sanitize_order_text(raw: str) -> str:
    """Strip whitespace and cap length to mitigate prompt-injection risk."""
    sanitized = raw.strip()
    if len(sanitized) > MAX_ORDER_TEXT_LENGTH:
        sanitized = sanitized[:MAX_ORDER_TEXT_LENGTH]
    # Remove any control characters except common whitespace
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)
    return sanitized


def _fallback_regex_parse(order_text: str) -> Optional[Dict[str, Any]]:
    """Simple regex fallback parser for standard warehouse order patterns when LLM is unavailable."""
    pattern = r"^(?:move|pick|fetch|transport|carry|shift|transfer)\s+(?:(\d+)\s+)?(.+?)\s+from\s+(.+?)\s+to\s+(.+)$"
    match = re.search(pattern, order_text, re.IGNORECASE)
    if match:
        qty_str, item, source, dest = match.groups()
        quantity = int(qty_str) if qty_str else 1
        return {
            "item": item.strip(),
            "quantity": quantity,
            "source": source.strip(),
            "destination": dest.strip().rstrip(".")
        }
    return None


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def parse_order(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Parse natural-language order text into a structured dict via Gemini/Groq LLM or regex fallback.

    On success  → sets parsed_order and status="parsed".
    On failure  → sets status="parse_failed" (handled by clarify_order downstream).
    """
    raw_input = state.get("order_text") or state.get("order_raw", "")
    order_text = _sanitize_order_text(raw_input)

    if not order_text:
        logger.warning("parse_order received empty order_text")
        return {"parsed_order": None, "status": "parse_failed"}

    prompt = ORDER_PARSE_PROMPT.format(order_text=order_text)

    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            fallback = _fallback_regex_parse(order_text)
            if fallback:
                logger.info("GROQ_API_KEY not set; parsed order via regex fallback: %s", fallback)
                return {"parsed_order": fallback, "status": "parsed"}
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
        parsed = json.loads(raw_text)

        # Validate expected keys
        required_keys = {"item", "quantity", "source", "destination"}
        if not required_keys.issubset(parsed.keys()):
            missing = required_keys - set(parsed.keys())
            logger.error("Groq response missing keys: %s", missing)
            fallback = _fallback_regex_parse(order_text)
            if fallback:
                return {"parsed_order": fallback, "status": "parsed"}
            return {"parsed_order": None, "status": "parse_failed"}

        logger.info("Order parsed successfully: %s", parsed)
        return {"parsed_order": parsed, "status": "parsed"}

    except json.JSONDecodeError as exc:
        logger.error("JSONDecodeError while parsing response: %s", exc)
        fallback = _fallback_regex_parse(order_text)
        if fallback:
            return {"parsed_order": fallback, "status": "parsed"}
        return {"parsed_order": None, "status": "parse_failed"}
    except Exception as exc:
        logger.error("Unexpected error in parse_order: %s", exc)
        fallback = _fallback_regex_parse(order_text)
        if fallback:
            logger.info("Parsed order via fallback regex after LLM error: %s", fallback)
            return {"parsed_order": fallback, "status": "parsed"}
        return {"parsed_order": None, "status": "parse_failed"}
