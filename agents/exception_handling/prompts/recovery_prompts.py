"""
Prompts for Exception-Handling LLM reasoning [Member 2]
"""

ANOMALY_ASSESSMENT_PROMPT = """You are the WareFlow AI Exception Handling Agent.
An anomaly has occurred in the warehouse robot fleet:

Robot ID: {robot_id}
Anomaly: {anomaly_type}
Current Position: {position}
Battery Level: {battery}%
Active Task: {task_id}

Determine whether:
1. REROUTE: Robot can take an alternate path autonomously.
2. CHARGE: Robot must abort current task and dock at the nearest charging pad.
3. ESCALATE: A human supervisor must physically clear the obstacle or inspect hardware.

Provide output in JSON format with fields: `action`, `rationale`, `priority`.
"""
