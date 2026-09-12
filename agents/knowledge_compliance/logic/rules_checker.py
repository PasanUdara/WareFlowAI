"""
Warehouse Safety Rules Evaluator [Member 3]
Deterministic validation logic for payload limits, speed caps, and hazmat restrictions.
"""

from typing import Dict, Any, List


class RulesChecker:
    """Evaluates task execution parameters against hardcoded warehouse limits."""

    MAX_STANDARD_PAYLOAD_KG = 50.0
    MAX_HEAVY_PAYLOAD_KG = 100.0
    MAX_HAZMAT_SPEED_MS = 0.8
    MAX_NORMAL_SPEED_MS = 2.0

    def evaluate(self, task_params: Dict[str, Any]) -> List[str]:
        """
        Evaluate proposed task against safety thresholds.
        
        Args:
            task_params: Dict containing payload_weight_kg, proposed_speed_ms, is_hazmat, target_zone.
            
        Returns:
            List of violation strings (empty list if fully compliant).
        """
        violations = []
        payload = task_params.get("payload_weight_kg", 0.0)
        speed = task_params.get("proposed_speed_ms", 1.0)
        is_hazmat = task_params.get("is_hazmat", False)
        
        # Check payload capacity
        if payload > self.MAX_HEAVY_PAYLOAD_KG:
            violations.append(
                f"Payload {payload}kg exceeds maximum AMR limit of {self.MAX_HEAVY_PAYLOAD_KG}kg (SOP-SPD-003)."
            )
            
        # Check hazardous speed limit
        if is_hazmat and speed > self.MAX_HAZMAT_SPEED_MS:
            violations.append(
                f"Hazmat speed {speed}m/s exceeds safety limit of {self.MAX_HAZMAT_SPEED_MS}m/s (SOP-HAZ-002)."
            )
            
        # Check general corridor speed
        if speed > self.MAX_NORMAL_SPEED_MS:
            violations.append(
                f"Proposed speed {speed}m/s exceeds maximum aisle velocity of {self.MAX_NORMAL_SPEED_MS}m/s (SOP-SPD-003)."
            )
            
        return violations
