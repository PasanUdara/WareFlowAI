"""
Interactive verification script for Task Planning Agent [Groq LLM].
Loads environment variables from .env and executes sample orders through the LangGraph pipeline.
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Find and load .env from the project root
root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

from agents.task_planning.graph import build_task_planning_graph
from agents.task_planning.state import TaskPlanningState


def test_agent_with_order(order_text: str):
    print("=" * 70)
    print(f"[INPUT ORDER] \"{order_text}\"")
    print("=" * 70)

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key or "your-groq-api-key" in api_key:
        print("\n[!] ERROR: GROQ_API_KEY is not set or still has a placeholder value in .env!")
        print("    Please edit .env and set your Groq API key: GROQ_API_KEY=gsk_...\n")
        return False

    model_name = os.environ.get("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    print(f"[+] LLM Provider: Groq ({model_name})")
    print("[*] Compiling & invoking LangGraph workflow...\n")

    graph = build_task_planning_graph()

    initial_state: TaskPlanningState = {
        "order_text": order_text,
        "parsed_order": None,
        "subtasks": None,
        "available_robots": ["AMR-01", "AMR-02", "AMR-03"],
        "assigned_robot": None,
        "status": "pending",
    }

    result = graph.invoke(initial_state)

    print("[*] RESULT STATE:")
    print(f"  - Lifecycle Status : {result.get('status')}")
    print(f"  - Assigned Robot   : {result.get('assigned_robot')}")
    print(f"  - Parsed Order     : {json.dumps(result.get('parsed_order'), indent=4)}")
    print(f"  - Subtasks ({len(result.get('subtasks') or [])} steps):")
    for step in result.get("subtasks") or []:
        print(f"      Step {step.get('step')}: {step.get('action').upper()} -> target: {step.get('target')}, item: {step.get('item')}, qty: {step.get('qty')}")
    print("=" * 70)

    if result.get("status") == "assigned":
        print("[SUCCESS] Agent parsed order, decomposed tasks, and assigned robot successfully!\n")
        return True
    else:
        print(f"[NOTICE] Non-success status: {result.get('status')}\n")
        return False


if __name__ == "__main__":
    test_order = sys.argv[1] if len(sys.argv) > 1 else "Move 5 boxes of surgical gloves from Shelf-B2 to Packing-Station-3"
    test_agent_with_order(test_order)
