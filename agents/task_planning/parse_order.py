"""
LangGraph Node: parse_order [Member 1]
Parses incoming natural language warehouse orders into structured order entities.
"""

from typing import Dict, Any
from .state import TaskPlanningState


def parse_order(state: TaskPlanningState) -> Dict[str, Any]:
    """
    Parse natural language order into structured data.
    
    Args:
        state: Current TaskPlanningState containing raw order string.
        
    Returns:
        State dictionary update containing 'parsed_order' and updated 'status'.
    """
    order_raw = state.get("order_raw", "")
    
    # TODO: [Member 1] Integrate LangChain/OpenAI prompt to extract:
    # - sku / item name
    # - quantity
    # - source shelf / aisle
    # - destination packing station / drop-off
    
    # Minimal placeholder parse logic for initial testing
    placeholder_parsed = {
        "order_id": "ORD-001",
        "raw_text": order_raw,
        "items": [
            {
                "sku": "SKU-MED-01",
                "quantity": 2,
                "source": "Shelf-A1",
                "destination": "Packing-Station-1"
            }
        ],
        "priority": "STANDARD"
    }
    
    return {
        "parsed_order": placeholder_parsed,
        "status": "PARSED"
    }
