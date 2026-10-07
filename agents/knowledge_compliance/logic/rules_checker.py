"""
Warehouse Safety Rules Evaluator [Member 3]
Deterministic validation logic for payload limits, speed caps,
hazmat restrictions, and battery safety.
"""

from typing import Dict, Any, List


class RulesChecker:
    """Evaluates task execution parameters against warehouse safety limits."""

    MAX_STANDARD_PAYLOAD_KG = 50.0
    MAX_HEAVY_PAYLOAD_KG = 100.0

    MAX_HAZMAT_SPEED_MS = 0.8
    MAX_NORMAL_SPEED_MS = 2.0

    MIN_BATTERY_FOR_NEW_TASK_PERCENT = 15.0

    def evaluate(self, task_params: Dict[str, Any]) -> List[str]:
        """
        Evaluate proposed task against warehouse safety thresholds.

        Supported input names:
            payload_weight_kg / payload_weight
            proposed_speed_ms / speed
            is_hazmat
            target_zone
            battery_level / battery_percentage / battery_percent

        Returns:
            List of violation strings.
            Empty list means the task is compliant.
        """

        violations: List[str] = []

        # ---------------------------------------------------------
        # 1. Read task parameters
        # ---------------------------------------------------------

        # Support both Member 3 naming and integration naming.
        payload = task_params.get(
            "payload_weight_kg",
            task_params.get("payload_weight", 0.0)
        )

        speed = task_params.get(
            "proposed_speed_ms",
            task_params.get("speed", 1.0)
        )

        is_hazmat = task_params.get("is_hazmat", False)

        # Support a few common battery field names.
        battery_level = task_params.get(
            "battery_level",
            task_params.get(
                "battery_percentage",
                task_params.get("battery_percent")
            )
        )

        # Convert numeric values safely.
        try:
            payload = float(payload)
        except (TypeError, ValueError):
            violations.append(
                "Invalid payload weight. A numeric payload value is required."
            )
            payload = 0.0

        try:
            speed = float(speed)
        except (TypeError, ValueError):
            violations.append(
                "Invalid speed value. A numeric speed value is required."
            )
            speed = 0.0

        # ---------------------------------------------------------
        # 2. Payload capacity check
        # ---------------------------------------------------------

        if payload > self.MAX_HEAVY_PAYLOAD_KG:
            violations.append(
                f"Payload {payload}kg exceeds maximum AMR limit of "
                f"{self.MAX_HEAVY_PAYLOAD_KG}kg (SOP-SPD-003)."
            )

        # ---------------------------------------------------------
        # 3. Hazmat speed check
        # ---------------------------------------------------------

        if is_hazmat and speed > self.MAX_HAZMAT_SPEED_MS:
            violations.append(
                f"Hazmat speed {speed}m/s exceeds safety limit of "
                f"{self.MAX_HAZMAT_SPEED_MS}m/s (SOP-HAZ-002)."
            )

        # ---------------------------------------------------------
        # 4. General speed check
        # ---------------------------------------------------------

        if speed > self.MAX_NORMAL_SPEED_MS:
            violations.append(
                f"Proposed speed {speed}m/s exceeds maximum aisle velocity "
                f"of {self.MAX_NORMAL_SPEED_MS}m/s (SOP-SPD-003)."
            )

        # ---------------------------------------------------------
        # 5. Battery safety check
        # ---------------------------------------------------------

        if battery_level is not None:
            try:
                battery_level = float(battery_level)

                if battery_level < self.MIN_BATTERY_FOR_NEW_TASK_PERCENT:
                    violations.append(
                        f"Battery level {battery_level}% is below the minimum "
                        f"{self.MIN_BATTERY_FOR_NEW_TASK_PERCENT}% required "
                        f"for starting a new task "
                        f"(SOP-BAT-001)."
                    )

            except (TypeError, ValueError):
                violations.append(
                    "Invalid battery level. A numeric battery percentage "
                    "is required."
                )

        return violations