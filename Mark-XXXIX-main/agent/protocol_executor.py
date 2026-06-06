"""Protocol Executor — Body-side intent creator for Mark XXXIX.

This replaces executor.py with a thin Intent creator that delegates
all reasoning to the soul via SoulBodyProtocol.

Principle: Mark XXXIX never directly invokes a tool. It sends intents
to the soul. The soul decides what executes. The body just renders.

Usage:
    from agent.protocol_executor import ProtocolExecutor

    executor = ProtocolExecutor(protocol)
    result = executor.execute(goal="Research AI safety and save it")
    speak(result.summary)
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from tools.embodiment.protocol import (
    Intent,
    IntentResult,
    IntentStatus,
    SoulBodyProtocol,
    TaskPriority,
)


class ProtocolExecutor:
    """Thin body-side executor that creates Intents and renders results.

    This replaces the old AgentExecutor which called _call_tool() directly.
    Now the body only creates Intents and renders IntentResults.
    """

    def __init__(self, protocol: SoulBodyProtocol):
        self._protocol = protocol

    def execute(
        self,
        goal: str,
        speak: Callable | None = None,
        cancel_flag: threading.Event | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        context: dict | None = None,
    ) -> str:
        """Execute a goal by sending it to the soul as an Intent.

        The body NEVER calls tools directly. It creates an Intent,
        sends it to the soul, and renders the result.

        Args:
            goal: What the user wants done
            speak: TTS callback for voice output
            cancel_flag: Event to signal cancellation
            priority: Task priority level
            context: Additional UI/session context

        Returns:
            Summary string for the user
        """
        # Step 1: Create Intent from goal (body's ONLY job)
        intent = Intent(
            raw_text=goal,
            user_id="current_user",
            session_id="current_session",
            timestamp=time.time(),
            context=context or {},
            priority=priority,
            speak_callback=speak,
            cancel_flag=cancel_flag,
        )

        # Step 2: Submit to soul via protocol (NEVER call tools directly)
        if speak:
            speak("Processing your request, sir.")

        future = self._protocol.submit_intent(intent)

        # Step 3: Wait for result
        try:
            result = future.result(timeout=300)  # 5 min timeout
        except Exception as e:
            return f"Task failed, sir. {e}"

        # Step 4: Render result (body's ONLY other job)
        return self._render_result(result, speak)

    def _render_result(
        self,
        result: IntentResult,
        speak: Callable | None,
    ) -> str:
        """Render an IntentResult in the HUD.

        This is the ONLY place where body touches output.
        """
        if result.status == IntentStatus.SUCCESS:
            if speak and result.summary:
                speak(result.summary)
            return result.summary or "Task completed, sir."

        elif result.status == IntentStatus.BLOCKED:
            msg = f"I cannot do that, sir. {result.blocking_reason}"
            if speak:
                speak(msg)
            return msg

        elif result.status == IntentStatus.APPROVAL_NEEDED:
            msg = (
                f"I need your approval to use {result.approval_request.tool_name}. "
                f"{result.approval_request.description}"
            )
            if speak:
                speak(msg)
            # Body shows approval dialog here
            # User approves → protocol.request_approval(intent_id, tool_call_id, True)
            # User denies → protocol.request_approval(intent_id, tool_call_id, False)
            return msg

        elif result.status == IntentStatus.FAILED:
            msg = f"Task failed, sir. {result.error}"
            if speak:
                speak(msg)
            return msg

        elif result.status == IntentStatus.CANCELLED:
            msg = "Task cancelled, sir."
            if speak:
                speak(msg)
            return msg

        return "Unknown status, sir."
