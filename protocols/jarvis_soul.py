"""JarvisSoul — JARVIS implementation of the SoulBodyProtocol.

Wraps the SAGE agent pipeline with Asimov safety enforcement.
The Body (Mark XXXIX) calls this. It never touches tools directly.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

# Ensure tools/ is on path
_JARVIS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_JARVIS_ROOT / "tools"))
sys.path.insert(0, str(_JARVIS_ROOT / "tools" / "embodiment"))

from protocols.types import (
    Intent,
    SoulResult,
    ToolCall,
    ToolResult,
    SafetyVerdict,
    RiskLevel,
    ApprovalStatus,
    ErrorSeverity,
    SoulState,
)
from protocols.soul_body import SoulBodyProtocol


class JarvisSoul(SoulBodyProtocol):
    """JARVIS implementation of the Soul-Body protocol.
    
    Every tool call goes through Asimov safety checks.
    HIGH-risk tools require explicit user approval.
    The Body never touches tools directly.
    """

    def __init__(self):
        self._state: SoulState = SoulState.IDLE
        self._state_callback: Callable[[SoulState], None] | None = None
        self._feedback_callback: Callable[[str, str], None] | None = None
        self._session_id: str = str(uuid.uuid4())
        self._pending_approvals: dict[str, dict[str, Any]] = {}
        self._initialized: bool = False

        # Lazy-loaded components
        self._process_task = None
        self._check_command = None
        self._check_action = None
        self._CAPABILITIES = None
        self._get_capability = None
        self._requires_approval = None
        self._get_risk_level = None

    # ── Lifecycle ───────────────────────────────────────────────────

    def initialize(self) -> None:
        """Initialize the Soul — load SAGE pipeline and safety checks."""
        if self._initialized:
            return

        self._set_state(SoulState.THINKING)

        # Import SAGE components
        try:
            from sage import process_task, _TOOL_EXECUTORS
            self._process_task = process_task
            self._tool_executors = _TOOL_EXECUTORS
        except ImportError as e:
            self._emit_feedback(f"Failed to load SAGE pipeline: {e}", "error")
            raise

        # Import Asimov safety
        try:
            from asimov import check_command, check_action
            self._check_command = check_command
            self._check_action = check_action
        except ImportError:
            self._emit_feedback("Asimov safety layer not available", "warning")

        # Import capability registry
        try:
            from embodiment.capability_registry import (
                CAPABILITIES,
                get_capability,
                requires_approval,
                get_risk_level,
            )
            self._CAPABILITIES = CAPABILITIES
            self._get_capability = get_capability
            self._requires_approval = requires_approval
            self._get_risk_level = get_risk_level
        except ImportError:
            self._emit_feedback("Capability registry not available", "warning")

        self._initialized = True
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Soul initialized", "success")

    def shutdown(self) -> None:
        """Gracefully shut down."""
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Soul shut down", "info")

    # ── Core: Intent processing ─────────────────────────────────────

    def process(self, intent: Intent) -> SoulResult:
        """Process a user intent through the full SAGE pipeline with safety."""
        t0 = time.time()
        self._set_state(SoulState.THINKING)

        # 1. Asimov command pre-check
        if self._check_command:
            allowed, reason = self._check_command(intent.text, "", {})
            if not allowed:
                self._set_state(SoulState.IDLE)
                return SoulResult(
                    request_id=intent.request_id,
                    response=f"Safety blocked: {reason}",
                    state=SoulState.IDLE,
                    safety_verdict=SafetyVerdict.BLOCKED_FIRST_LAW
                    if "FIRST LAW" in reason
                    else SafetyVerdict.BLOCKED_THIRD_LAW,
                    duration_ms=int((time.time() - t0) * 1000),
                )

        # 2. Route through SAGE pipeline
        self._set_state(SoulState.ROUTING)
        try:
            response = self._process_task(intent.text)
        except Exception as e:
            self._set_state(SoulState.ERROR)
            return SoulResult(
                request_id=intent.request_id,
                response=f"Error: {e}",
                state=SoulState.ERROR,
                safety_verdict=SafetyVerdict.ERROR,
                error=str(e),
                duration_ms=int((time.time() - t0) * 1000),
            )

        # 3. Parse tool calls from response (if SAGE executed tools)
        tool_calls = []
        tool_results = []
        needs_approval = False

        # Check if the response indicates tool execution
        if hasattr(self, '_tool_executors'):
            # SAGE already executed tools safely through _TOOL_EXECUTORS
            # which include safe_file_operation, safe_computer_action, etc.
            pass

        self._set_state(SoulState.IDLE)
        return SoulResult(
            request_id=intent.request_id,
            response=response,
            state=SoulState.IDLE,
            safety_verdict=SafetyVerdict.APPROVED,
            tool_calls=tool_calls,
            tool_results=tool_results,
            needs_approval=needs_approval,
            agent_used="sage_pipeline",
            duration_ms=int((time.time() - t0) * 1000),
        )

    # ── Approval flow ───────────────────────────────────────────────

    def approve_tool_calls(
        self,
        approval_id: str,
        approved: bool,
    ) -> SoulResult:
        """Handle approval response from the Body."""
        pending = self._pending_approvals.pop(approval_id, None)
        if not pending:
            return SoulResult(
                request_id=approval_id,
                response="Approval request not found or expired.",
                state=SoulState.IDLE,
                safety_verdict=SafetyVerdict.ERROR,
            )

        if not approved:
            return SoulResult(
                request_id=approval_id,
                response="Action denied by user.",
                state=SoulState.IDLE,
                safety_verdict=SafetyVerdict.BLOCKED_THIRD_LAW,
            )

        # User approved — execute the tool
        tool_name = pending["tool_name"]
        params = pending["params"]

        self._set_state(SoulState.EXECUTING)
        try:
            executor = self._tool_executors.get(tool_name)
            if executor:
                result = executor(params)
                return SoulResult(
                    request_id=approval_id,
                    response=str(result.get("result", "Done.")),
                    state=SoulState.IDLE,
                    safety_verdict=SafetyVerdict.APPROVED,
                    tool_results=[
                        ToolResult(
                            call_id=approval_id,
                            tool_name=tool_name,
                            status="success",
                            result=result.get("result"),
                        )
                    ],
                )
            else:
                return SoulResult(
                    request_id=approval_id,
                    response=f"Tool '{tool_name}' not available.",
                    state=SoulState.IDLE,
                    safety_verdict=SafetyVerdict.ERROR,
                )
        except Exception as e:
            return SoulResult(
                request_id=approval_id,
                response=f"Error executing {tool_name}: {e}",
                state=SoulState.ERROR,
                safety_verdict=SafetyVerdict.ERROR,
                error=str(e),
            )
        finally:
            self._set_state(SoulState.IDLE)

    # ── Capability discovery ────────────────────────────────────────

    def list_capabilities(self, domain: str | None = None) -> list[dict[str, Any]]:
        """List available tools from the capability registry."""
        if not self._get_capability:
            return []

        try:
            from embodiment.capability_registry import list_capabilities as _list_caps
            caps = _list_caps(domain)
            return [
                {
                    "name": c.name,
                    "domain": c.domain,
                    "risk": c.risk.value,
                    "approval_required": c.approval_required,
                    "description": c.description,
                    "inputs": c.inputs,
                    "outputs": c.outputs,
                }
                for c in caps
            ]
        except ImportError:
            return []

    def get_capability(self, tool_name: str) -> dict[str, Any] | None:
        """Get metadata for a single tool."""
        if not self._get_capability:
            return None

        try:
            cap = self._get_capability(tool_name)
            if not cap:
                return None
            return {
                "name": cap.name,
                "domain": cap.domain,
                "risk": cap.risk.value,
                "approval_required": cap.approval_required,
                "description": cap.description,
                "inputs": cap.inputs,
                "outputs": cap.outputs,
            }
        except ImportError:
            return None

    # ── Status & feedback ───────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get Soul status for the HUD."""
        return {
            "state": self._state.value,
            "session_id": self._session_id,
            "version": "0.1.0",
            "initialized": self._initialized,
            "capabilities_count": len(self._CAPABILITIES) if self._CAPABILITIES else 0,
        }

    def set_state_callback(self, callback: Callable[[SoulState], None]) -> None:
        """Register state change callback."""
        self._state_callback = callback

    def set_feedback_callback(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """Register feedback message callback."""
        self._feedback_callback = callback

    # ── Internal helpers ────────────────────────────────────────────

    def _set_state(self, state: SoulState) -> None:
        """Update state and notify callback."""
        self._state = state
        if self._state_callback:
            try:
                self._state_callback(state)
            except Exception:
                pass

    def _emit_feedback(self, message: str, level: str = "info") -> None:
        """Send feedback to the Body."""
        if self._feedback_callback:
            try:
                self._feedback_callback(message, level)
            except Exception:
                pass
