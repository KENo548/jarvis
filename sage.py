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

# ── Tool executors map ─────────────────────────────────────────────
# Maps tool names (as returned by Tool Operator) to callable functions.
# Each executor receives `params: dict` and returns a structured result dict.

_TOOL_EXECUTORS: dict[str, callable] = {}

try:
    from embodiment.open_app import launch as _launch_app
    _TOOL_EXECUTORS["open_app"] = lambda params: {
        "tool": "app_launcher", "status": "executed",
        "result": _launch_app(params.get("app_name", "")),
    }
except ImportError:
    pass

try:
    from embodiment.browser_control import browser_control as _browser_control
    _TOOL_EXECUTORS["browser_control"] = lambda params: {
        "tool": "browser_navigation", "status": "executed",
        "result": _browser_control(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.web_search import web_search as _web_search
    _TOOL_EXECUTORS["web_search"] = lambda params: {
        "tool": "web_search", "status": "executed",
        "result": _web_search(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.vision import Vision as _Vision
    _TOOL_EXECUTORS["screen_vision"] = lambda params: {
        "tool": "screen_vision", "status": "executed",
        "result": _Vision.analyze_screen(
            params.get("question", "What do you see on this screen?")
        ).description,
    }
except ImportError:
    pass

try:
    from embodiment.code_helper import code_helper as _code_helper
    _TOOL_EXECUTORS["code_helper"] = lambda params: {
        "tool": "code_generation", "status": "executed",
        "result": _code_helper(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.weather_report import weather_action as _weather_action
    _TOOL_EXECUTORS["weather_report"] = lambda params: {
        "tool": "weather", "status": "executed",
        "result": _weather_action(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.reminder import reminder as _reminder
    _TOOL_EXECUTORS["reminder"] = lambda params: {
        "tool": "reminders", "status": "executed",
        "result": _reminder(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.youtube_video import youtube_video as _youtube_video
    _TOOL_EXECUTORS["youtube"] = lambda params: {
        "tool": "youtube", "status": "executed",
        "result": _youtube_video(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.desktop import desktop_control as _desktop_control
    _TOOL_EXECUTORS["desktop_control"] = lambda params: {
        "tool": "desktop_control", "status": "executed",
        "result": _desktop_control(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.flight_finder import flight_finder as _flight_finder
    _TOOL_EXECUTORS["flight_search"] = lambda params: {
        "tool": "flight_search", "status": "executed",
        "result": _flight_finder(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.send_message import send_message as _send_message
    _TOOL_EXECUTORS["messaging"] = lambda params: {
        "tool": "messaging", "status": "executed",
        "result": _send_message(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.game_updater import game_updater as _game_updater
    _TOOL_EXECUTORS["game_updater"] = lambda params: {
        "tool": "game_updater", "status": "executed",
        "result": _game_updater(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.file_processor import file_processor as _file_processor
    _TOOL_EXECUTORS["file_processor"] = lambda params: {
        "tool": "file_processor", "status": "executed",
        "result": _file_processor(parameters=params),
    }
except ImportError:
    pass

try:
    from embodiment.dev_agent import dev_agent as _dev_agent
    _TOOL_EXECUTORS["project_builder"] = lambda params: {
        "tool": "project_builder", "status": "executed",
        "result": _dev_agent(parameters=params),
    }
except ImportError:
    pass


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

    # ── Asimov command pre-check (before any agent dispatch) ─────────────
    try:
        from tools.asimov import check_command
        asimov_allowed, asimov_reason = check_command(task_text, "", {})
        if not asimov_allowed:
            response = f"Asimov safety layer blocked this request.\n\n{asimov_reason}"
            log_interaction(
                agent_name="asimov",
                input_text=task_text,
                output_text=response,
                model="asimov",
                duration_ms=0,
                session_id=SESSION_ID,
                task_id=str(uuid.uuid4()),
                memory_context_snapshot={},
                tool_calls_made=[],
                reasoning_trace=asimov_reason,
                domain="safety",
            )
            return response
    except ImportError:
        pass  # Asimov module not available — proceed without pre-check

    # 1. Commander routes the task
    route = route_task(task_text)
    agent = route.get("selected_agent", "tool_operator")

    # 2. Dispatch to the right agent
    if agent == "planner":
        result = create_plan(task_text)
        steps = result.get("steps", [])
        summary = result.get("summary", "")

        if steps:
            response = f"Here's my plan:\n\n"
            for s in steps:
                step_num = s.get("step", "?")
                desc = s.get("description", "No description")
                response += f"  {step_num}. {desc}\n"
            if summary:
                response += f"\n{summary}"
        else:
            response = "I can help you plan that. Could you provide more details about what you'd like to accomplish?"
    elif agent == "engineer":
        result = generate_code(task_text)
        explanation = result.get("explanation", "Code generated.")
        code = result.get("code", "")
        language = result.get("language", "python")

        if code:
            response = f"{explanation}\n\n```{language}\n{code}\n```"
        else:
            response = explanation
    elif agent == "researcher":
        result = research_topic(task_text)
        # Extract full summary
        summary = result.get("summary", "Research complete.")
        key_findings = result.get("key_findings", [])
        sources = result.get("sources", [])

        # Build full response
        response = summary
        if key_findings:
            response += "\n\nKey findings:\n" + "\n".join(f"  \u2022 {f}" for f in key_findings)
        if sources:
            response += "\n\nSources:\n" + "\n".join(f"  \u2022 {s}" for s in sources)
    elif agent == "memory_coordinator":
        result = coordinate_memory(task_text)
        # Memory updates are already handled by coordinate_memory (Chroma + JSON fallback)
        memory_updates = result.get("memory_updates", {})
        if memory_updates:
            response = f"Memory updated: {len(memory_updates)} category(ies). {result.get('context_assembly', '')}"
        else:
            response = result.get("context_assembly", "Memory analyzed, no updates needed.")
    else:
        result = plan_tool_usage(task_text)
        tool_calls = result.get("tool_calls", [])
        tool_response = result.get("response", "")

        # If no tools needed and there's a response, use it
        if not tool_calls and tool_response:
            response = tool_response
        else:
            # Execute tool calls with approval gates
            executed = []
            for tc in tool_calls:
                tool_name = tc.get("tool", "")
                params = tc.get("params", {})

                # 1. Check tool executors map (embodiment tools)
                executor = _TOOL_EXECUTORS.get(tool_name)
                if executor:
                    exec_result = executor(params)
                # 2. Route through safe wrappers for HIGH-risk tools
                elif tool_name == "file_controller" and safe_file_operation:
                    exec_result = safe_file_operation(params)
                elif tool_name == "computer_control" and safe_computer_action:
                    exec_result = safe_computer_action(params)
                elif tool_name == "computer_settings" and safe_system_setting:
                    exec_result = safe_system_setting(params)
                else:
                    # Unknown tool — provide a meaningful unavailable response
                    exec_result = {
                        "tool": tool_name,
                        "status": "unavailable",
                        "result": f"Tool '{tool_name}' is not available in this environment."
                    }

                executed.append(exec_result)

            if executed:
                details = []
                result_texts = []
                for e in executed:
                    tool = e.get("tool", tool_name)
                    status = e.get("status", "done")
                    details.append(f"{tool} ({status})")
                    raw = e.get("result", "")
                    if isinstance(raw, dict):
                        raw = str(raw.get("result", raw.get("status", str(raw))))
                    if isinstance(raw, str) and raw and raw not in result_texts:
                        result_texts.append(raw)

                response = " | ".join(details)
                if any(e.get("needs_approval") for e in executed):
                    pending = [e for e in executed if e.get("needs_approval")]
                    response += f" | {len(pending)} awaiting approval."
                if result_texts:
                    response += "\n" + "\n".join(result_texts[:3])
            else:
                response = "No tools were needed for this task."

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
    parser.add_argument("--voice", action="store_true", help="Voice mode (terminal)")
    parser.add_argument("--test", action="store_true", help="Run E2E verification")
    parser.add_argument("--providers", action="store_true", help="List LLM providers")
    parser.add_argument("--stats", action="store_true", help="Show interaction stats")
    parser.add_argument("--text", action="store_true", help="Text-only mode (no UI)")
    parser.add_argument("--ui", action="store_true", help="Launch PyQt6 GUI (with voice)")
    parser.add_argument("--no-voice", action="store_true", help="Launch UI without voice")
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
    elif args.text:
        text_mode()
    else:
        # All UI modes delegate to Mark-XXXIX main.py (the only Soul-protected entry point)
        import subprocess
        main_py = Path(__file__).resolve().parent / "Mark-XXXIX-main" / "main.py"
        print(f"  SAGE — delegating to {main_py}")
        sys.exit(subprocess.call([sys.executable, str(main_py)] + (["--no-voice"] if args.no_voice else [])))
