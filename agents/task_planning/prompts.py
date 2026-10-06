"""
Prompt Templates for Task Planning Agent [Member 1]
All LLM prompt templates as named string constants, separated from node logic
so they can be tuned independently and referenced in documentation.
"""

# ---------------------------------------------------------------------------
# ORDER PARSING PROMPT
# ---------------------------------------------------------------------------
ORDER_PARSE_PROMPT = """\
You are the WareFlow AI order-parsing assistant.
Given a natural-language warehouse order, extract the following fields and return
them as a single flat JSON object (no markdown fences, no extra keys):

{{
  "item": "<name or SKU of the item>",
  "quantity": <integer>,
  "source": "<warehouse location to pick from>",
  "destination": "<delivery location>"
}}

Rules:
- "quantity" MUST be a positive integer. If the order does not specify a quantity,
  default to 1.
- If a field cannot be determined, set its value to "UNKNOWN".
- Output ONLY the JSON object — no explanation, no commentary.

Order: {order_text}
"""


# ---------------------------------------------------------------------------
# TASK DECOMPOSITION PROMPT
# ---------------------------------------------------------------------------
TASK_DECOMPOSE_PROMPT = """\
You are the WareFlow AI task-decomposition assistant.
Given a structured warehouse order (JSON), break it down into an ordered list of
low-level robot actions.

Parsed order:
{parsed_order_json}

Produce a JSON object with a "steps" key containing an array of step objects:
{{
  "steps": [
    {{
      "step": 1,
      "action": "<one of: navigate, pick, drop>",
      "target": "<location or item name relevant to the action>",
      "item": "<item being handled, if applicable, else null>",
      "qty": <quantity being handled, if applicable, else null>
    }}
  ]
}}

Typical sequence for a single-item order:
1. navigate to source location
2. pick the item
3. navigate to destination location
4. drop the item

Output ONLY the JSON object — no markdown fences, no commentary.
"""
