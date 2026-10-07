"""
Prompt Injection Sanitization Module [Member 4]
Filters and sanitizes natural language inputs to protect LLM agents against prompt injection attacks.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("wareflow.security.sanitization")

# System prompt injection patterns
INJECTION_PATTERNS = [
    (r"ignore (all )?previous instructions", "System instruction override attempt"),
    (r"system prompt", "Referencing system prompt internals"),
    (r"disregard (all )?prior rules", "Rule override attempt"),
    (r"you are now (an? )?", "Persona hijacking attempt"),
    (r"act as an? (unrestricted|evil|admin)", "Privilege escalation attempt"),
    (r"bypass safety", "Safety bypass attempt"),
    (r"dump (all )?data", "Data exfiltration attempt"),
    (r"print (your|the) prompt", "Prompt extraction attempt"),
    (r"drop table|exec\(|eval\(|<script", "Code/Script injection attempt")
]

COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in INJECTION_PATTERNS]


def sanitize_user_input(user_input: str) -> Dict[str, Any]:
    """
    Sanitize and inspect natural language input text against prompt injection patterns.
    
    Args:
        user_input: Raw natural language command string.
        
    Returns:
        Structured dict containing:
          - allowed (bool): True if input is safe to process.
          - sanitized_text (str): Cleaned text.
          - reason (Optional[str]): Explanation if rejected.
    """
    if not user_input or not user_input.strip():
        return {
            "allowed": True,
            "sanitized_text": "",
            "reason": None
        }

    # Remove control characters except standard whitespace
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", user_input).strip()

    # Check against compiled prompt injection regexes
    for compiled_regex, reason in COMPILED_PATTERNS:
        if compiled_regex.search(cleaned):
            logger.warning("[Security Guard] Prompt injection detected ('%s'): '%s'", reason, user_input)
            return {
                "allowed": False,
                "sanitized_text": cleaned,
                "reason": f"Security violation: {reason}"
            }

    return {
        "allowed": True,
        "sanitized_text": cleaned,
        "reason": None
    }


def sanitize_prompt_input(user_input: str) -> str:
    """
    Legacy wrapper function returning sanitized string or raising ValueError if rejected.
    """
    result = sanitize_user_input(user_input)
    if not result["allowed"]:
        raise ValueError(result["reason"])
    return result["sanitized_text"]
