"""
Exception-Handling Agent Package [Member 2]
Monitors simulated AMR events (stuck robot, critical battery, blocked paths)
and executes autonomous recovery strategies (reroute vs. escalate to human).
"""

from .agent import ExceptionHandlingAgent

__all__ = ["ExceptionHandlingAgent"]
