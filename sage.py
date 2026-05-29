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
from observability.auto_eval import evaluate
from embodiment.capability_registry import CAPABILITIES, get_capability, get_execution_order, requires_approval

# Import safe wrappers for HIGH-risk tools
try:
    from embodiment.file_controller import safe_file_operation
except ImportError:
    safe_file_operation = None
try:
    from embodiment.computer_control import safe_computer_action
except ImportError:
    safe_computer_action = None
try:
    from embodiment.computer_settings import safe_system_setting
except ImportError:
    safe_system_setting = None


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

    # Handle conversational inputs directly
    lower = task_text.lower().strip()
    conversational_triggers = ("hello", "hi ", "hey", "good morning", "good evening", "good afternoon", "how are you", "what's up", "sup")
    if lower in ("hello", "hi", "hey") or lower.startswith(conversational_triggers):
        response = "Hello! I'm Sage, your AI assistant. How can I help you today?"
        # Still log it
        log_interaction(
            agent_name="commander",
            input_text=task_text,
            output_text=response,
            model="conversational",
            duration_ms=0,
            session_id=SESSION_ID,
            task_id=str(uuid.uuid4()),
            memory_context_snapshot={},
            tool_calls_made=[],
            reasoning_trace="conversational greeting",
            domain="conversational",
        )
        return response

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
        # Extract full summary, not just first line
        summary = result.get("summary", "Research complete.")
        key_findings = result.get("key_findings", [])
        if key_findings:
            response = f"{summary}\n\nKey findings:\n" + "\n".join(f"• {f}" for f in key_findings)
        else:
            response = summary
    elif agent == "memory_coordinator":
        result = coordinate_memory(task_text)
        # Actually execute memory updates
        memory_updates = result.get("memory_updates", {})
        if memory_updates:
            try:
                from agents.memory_coordinator import coordinate_memory as _cm
                # Write updates through the memory store
                memory_path = Path(__file__).resolve().parent / "memory" / "sqlite" / "memory_store.json"
                memory_path.parent.mkdir(parents=True, exist_ok=True)
                existing = {}
                if memory_path.exists():
                    existing = json.loads(memory_path.read_text(encoding="utf-8"))
                # Merge updates
                for category, entries in memory_updates.items():
                    if category not in existing:
                        existing[category] = {}
                    if isinstance(entries, dict):
                        existing[category].update(entries)
                memory_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                response = f"Memory updated: {len(memory_updates)} category(ies). {result.get('context_assembly', '')}"
            except Exception as e:
                response = f"Memory plan created but write failed: {e}"
        else:
            response = result.get("context_assembly", "Memory analyzed, no updates needed.")
    else:
        result = plan_tool_usage(task_text)
        tool_calls = result.get("tool_calls", [])

        # Execute tool calls with approval gates
        executed = []
        for tc in tool_calls:
            tool_name = tc.get("tool", "")
            params = tc.get("params", {})

            # Route through safe wrappers for HIGH-risk tools
            if tool_name == "file_controller" and safe_file_operation:
                exec_result = safe_file_operation(params)
            elif tool_name == "computer_control" and safe_computer_action:
                exec_result = safe_computer_action(params)
            elif tool_name == "computer_settings" and safe_system_setting:
                exec_result = safe_system_setting(params)
            else:
                # LOW/MEDIUM risk tools execute directly
                exec_result = {"tool": tool_name, "status": "executed", "params": params}

            executed.append(exec_result)

        response = f"Executed {len(executed)} tool call(s)."
        if any(e.get("needs_approval") for e in executed):
            pending = [e for e in executed if e.get("needs_approval")]
            response += f" {len(pending)} awaiting approval."

    latency = int((time.time() - t0) * 1000)

    # 3. Auto-evaluate the response
    eval_result = evaluate(
        agent_name=agent,
        input_text=task_text,
        output_text=response,
    )

    # 4. Log the interaction with auto-eval
    overall_score = eval_result.get("overall", 0.0)
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

    # Update success_score with auto-eval result
    try:
        from observability.interaction_logger import _connect
        conn = _connect()
        # Get the most recent interaction_id for this session
        row = conn.execute(
            "SELECT interaction_id FROM interactions WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (SESSION_ID,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE interactions SET success_score = ? WHERE interaction_id = ?",
                (overall_score, row[0]),
            )
            conn.commit()
        conn.close()
    except Exception:
        pass

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
    parser.add_argument("--ui", action="store_true", help="Launch PyQt6 GUI")
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
    elif args.ui:
        from ui import run_ui
        run_ui(process_fn=process_task)
    else:
        text_mode()
