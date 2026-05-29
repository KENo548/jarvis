#!/usr/bin/env python3
"""SAGE — The single entry point for the cognitive operating system.

Usage:
    python sage.py                    # Interactive text mode
    python sage.py --voice            # Voice mode (microphone + TTS)
    python sage.py --test             # Run E2E verification
    python sage.py --providers        # List available LLM providers
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

# Ensure tools/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "tools" / "embodiment"))

from llm_client import llm_call, list_providers
from agents.commander import route_task
from agents.planner import create_plan
from agents.engineer import generate_code
from agents.researcher import research_topic
from agents.memory_coordinator import coordinate_memory
from agents.tool_operator import plan_tool_usage
from observability.interaction_logger import init_db, log_interaction, get_stats
from embodiment.capability_registry import CAPABILITIES, get_capability, get_execution_order


VERSION = "0.1.0"
SESSION_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are SAGE, a cognitive operating system. You are efficient, professional, and direct.

You have these capabilities:
- Route tasks to the right specialist agent
- Plan multi-step workflows
- Generate and execute code
- Research topics using web search and memory
- Control the computer (launch apps, browser, files, OS settings)
- Remember user preferences and context

For every user request:
1. Understand the intent
2. Route to the right agent/tool
3. Execute and report results briefly
4. Log the interaction

Be concise. No fluff. Action-oriented."""


# ---------------------------------------------------------------------------
# Agent pipeline
# ---------------------------------------------------------------------------

def process_task(task_text: str) -> str:
    """Route a task through the SAGE agent pipeline."""
    t0 = time.time()

    # 1. Commander routes the task
    route = route_task(task_text)
    agent = route.get("selected_agent", "tool_operator")

    # 2. Dispatch to the right agent
    if agent == "planner":
        result = create_plan(task_text)
        response = f"Plan: {len(result.get('steps', []))} steps created."
    elif agent == "engineer":
        result = generate_code(task_text)
        response = result.get("explanation", "Code generated.")
    elif agent == "researcher":
        result = research_topic(task_text)
        response = result.get("summary", "Research complete.")
    elif agent == "memory_coordinator":
        result = coordinate_memory(task_text)
        response = result.get("context_assembly", "Memory updated.")
    else:
        result = plan_tool_usage(task_text)
        tool_calls = result.get("tool_calls", [])
        response = f"Planned {len(tool_calls)} tool call(s)."

    latency = int((time.time() - t0) * 1000)

    # 3. Log the interaction
    log_interaction(
        agent_name=agent,
        input_text=task_text,
        output_text=response,
        model=route.get("route", {}).get("model", "ollama/llama3.2"),
        duration_ms=latency,
        session_id=SESSION_ID,
        task_id=str(uuid.uuid4()),
        memory_context_snapshot={},
        tool_calls_made=[],
        reasoning_trace=json.dumps(route),
        domain="general",
    )

    return response


# ---------------------------------------------------------------------------
# Interactive text mode
# ---------------------------------------------------------------------------

def text_mode():
    """Interactive text-based conversation."""
    print(f"\n  SAGE v{VERSION} — Cognitive Operating System")
    print(f"  Session: {SESSION_ID[:8]}...")
    print(f"  Type 'exit' to quit, 'stats' for statistics, 'providers' for LLM info\n")

    init_db()

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSAGE > Goodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("SAGE > Goodbye.")
            break
        if user_input.lower() == "stats":
            stats = get_stats()
            print(f"SAGE > {json.dumps(stats, indent=2)}")
            continue
        if user_input.lower() == "providers":
            for p in list_providers():
                status = "OK" if p["online"] else "--"
                print(f"  {status} {p['name']:40s} {p['type']:5s}")
            continue

        response = process_task(user_input)
        print(f"SAGE > {response}\n")


# ---------------------------------------------------------------------------
# Voice mode
# ---------------------------------------------------------------------------

def voice_mode():
    """Voice-based conversation using Whisper + Edge TTS."""
    try:
        from embodiment.voice_io import voice_loop
    except ImportError:
        print("Voice dependencies not installed. Run:")
        print("  pip install sounddevice numpy edge-tts")
        return

    print(f"\n  SAGE v{VERSION} — Voice Mode")
    print(f"  Say something or press Ctrl+C to stop\n")

    init_db()
    voice_loop(process_task, continuous=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE — Cognitive Operating System")
    parser.add_argument("--voice", action="store_true", help="Voice mode")
    parser.add_argument("--test", action="store_true", help="Run E2E verification")
    parser.add_argument("--providers", action="store_true", help="List LLM providers")
    parser.add_argument("--stats", action="store_true", help="Show interaction stats")
    args = parser.parse_args()

    if args.test:
        from tests.e2e_verification import run_all
        run_all()
    elif args.providers:
        for p in list_providers():
            status = "OK" if p["online"] else "--"
            print(f"  {status} {p['name']:40s} {p['type']:5s}")
    elif args.stats:
        init_db()
        print(json.dumps(get_stats(), indent=2))
    elif args.voice:
        voice_mode()
    else:
        text_mode()
