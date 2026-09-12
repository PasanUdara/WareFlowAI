"""
Task Decomposer Logic [Member 1]
Helper algorithms to split large orders based on SKU locations and AMR capacity limits.
"""

from typing import List, Dict, Any


def split_order_by_capacity(items: List[Dict[str, Any]], max_payload_kg: float = 50.0) -> List[List[Dict[str, Any]]]:
    """
    Split item list into payload-compliant batches.
    
    # TODO: [Member 1] Implement weight aggregation and multi-trip batching.
    """
    batches = []
    current_batch = []
    current_weight = 0.0
    
    for item in items:
        weight = item.get("weight_kg", 5.0) * item.get("quantity", 1)
        if current_weight + weight > max_payload_kg and current_batch:
            batches.append(current_batch)
            current_batch = [item]
            current_weight = weight
        else:
            current_batch.append(item)
            current_weight += weight
            
    if current_batch:
        batches.append(current_batch)
        
    return batches
