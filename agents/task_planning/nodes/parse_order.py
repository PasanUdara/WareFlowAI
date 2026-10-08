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


def _rule_based_parse_order(order_text: str) -> Optional[Dict[str, Any]]:
    """
    Deterministic rule-based order parser fallback when LLM is unavailable.
    Extracts item, quantity, source, and destination.
    """
    clean_text = order_text.strip().rstrip(".").rstrip(",")

    # Pattern 1: <Action> [Qty] <Item> from <Source> to <Destination>
    pattern1 = re.compile(
        r"^(?:fetch|move|transport|bring|carry|transfer|deliver|pick\s+up|shift)\s+"
        r"(?:(\d+)\s+)?(.*?)\s+from\s+(.*?)\s+to\s+(.*)$",
        re.IGNORECASE
    )
    # Pattern 2: <Action> [Qty] <Item> to <Destination> from <Source>
    pattern2 = re.compile(
        r"^(?:fetch|move|transport|bring|carry|transfer|deliver|pick\s+up|shift)\s+"
        r"(?:(\d+)\s+)?(.*?)\s+to\s+(.*?)\s+from\s+(.*)$",
        re.IGNORECASE
    )

    match1 = pattern1.match(clean_text)
    if match1:
        qty_str, item, source, destination = match1.groups()
        return {
            "item": item.strip(),
            "quantity": int(qty_str) if qty_str else 1,
            "source": source.strip(),
            "destination": destination.strip(),
        }

    match2 = pattern2.match(clean_text)
    if match2:
        qty_str, item, destination, source = match2.groups()
        return {
            "item": item.strip(),
            "quantity": int(qty_str) if qty_str else 1,
            "source": source.strip(),
            "destination": destination.strip(),
        }

    # Pattern 3: Generalized extraction if 'from' and 'to' are present
    if "from" in clean_text.lower() and "to" in clean_text.lower():
        sub_match = re.search(
            r"(?:(\d+)\s+)?(.*?)\s+from\s+(.*?)\s+to\s+(.*)$",
            clean_text,
            re.IGNORECASE
        )
        if sub_match:
            qty_str, item, source, destination = sub_match.groups()
            clean_item = re.sub(
                r"^(?:fetch|move|transport|bring|carry|transfer|deliver|pick\s+up|shift)\s+",
                "",
                item.strip(),
                flags=re.IGNORECASE
            )
            return {
                "item": clean_item.strip() or "item",
                "quantity": int(qty_str) if qty_str else 1,
                "source": source.strip(),
                "destination": destination.strip(),
            }

    return None


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------
def parse_order(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Parse natural-language order text into a structured dict via Groq LLM,
    falling back to a deterministic parser if LLM is unavailable or fails.

    On success  → sets parsed_order and status="parsed".
    On failure  → sets status="parse_failed" (handled by clarify_order downstream).
    """
    raw_input = state.get("order_text") or state.get("order_raw", "")
    order_text = _sanitize_order_text(raw_input)

    if not order_text:
        logger.warning("parse_order received empty order_text")
        return {"parsed_order": None, "status": "parse_failed"}

    # Attempt Groq LLM if API key is configured
    api_key = os.environ.get("GROQ_API_KEY", "")
    if api_key:
        try:
            model_name = os.environ.get("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
            client = Groq(api_key=api_key)
            prompt = ORDER_PARSE_PROMPT.format(order_text=order_text)

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
            else:
                logger.info("Order parsed successfully via Groq: %s", parsed)
                return {"parsed_order": parsed, "status": "parsed"}

        except json.JSONDecodeError as exc:
            logger.warning("JSONDecodeError while parsing Groq response: %s", exc)
        except Exception as exc:
            logger.warning("Unexpected error in Groq parse_order (%s), falling back to rule-based parser", exc)
    else:
        logger.info("GROQ_API_KEY not set. Using rule-based fallback parser.")

    # -----------------------------------------------------------------------
    # Deterministic rule-based fallback
    # -----------------------------------------------------------------------
    fallback_parsed = _rule_based_parse_order(order_text)
    if fallback_parsed:
        logger.info("Order parsed successfully via rule-based fallback: %s", fallback_parsed)
        return {"parsed_order": fallback_parsed, "status": "parsed"}

    logger.warning("Both Groq and rule-based parser failed to parse order: '%s'", order_text)
    return {"parsed_order": None, "status": "parse_failed"}
