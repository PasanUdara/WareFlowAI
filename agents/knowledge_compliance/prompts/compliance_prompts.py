"""
Prompts for Knowledge & Compliance RAG synthesis [Member 3]
"""

SOP_GROUNDING_PROMPT = """You are the WareFlow AI Compliance Verification Agent.
Evaluate whether the proposed warehouse operation complies with the provided SOP excerpts.

SOP Context:
{sop_context}

Proposed Operation:
- Item: {item_name}
- Weight: {weight_kg} kg
- Hazardous Classification: {is_hazmat}
- Proposed Route: {route_corridors}
- Speed: {speed_ms} m/s

State whether the operation is COMPLIANT or NON_COMPLIANT.
If non-compliant, cite the exact SOP section and explain the safety hazard.
"""
