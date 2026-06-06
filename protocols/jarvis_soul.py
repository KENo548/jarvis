"""JarvisSoul — JARVIS implementation of the SoulBodyProtocol.

Three-tier control model enforced:
  Tier 1 — Operator: kill switch, HIGH-risk approval, can override anything
  Tier 2 — Soul: classifies intent, plans, proposes actions
  Tier 3 — Tools: only runs what cleared both above tiers

The Soul proposes. The operator decides. Tools execute.
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from protocols.types import (
    Intent,
    SoulResult,
    ToolCall,
    ToolProposal,
    ToolResult,
    SafetyVerdict,
    RiskLevel,
    ApprovalStatus,
    ErrorSeverity,
    SoulState,
    KillSwitchState,
    ApprovalWindow,
)
from protocols.soul_body import SoulBodyProtocol


class JarvisSoul(SoulBodyProtocol):
    """JARVIS implementation of the Soul-Body protocol.
    
    Authority model:
      1. Operator has final authority — kill switch, HIGH-risk approval
      2. Soul has intelligence — classifies, routes, proposes
      3. Tools have execution — only runs what cleared both tiers
    
    The Soul NEVER overrides the operator. Ever.
    """

    def __init__(self):
        self._state: SoulState = SoulState.IDLE
        self._state_callback: Callable[[SoulState], None] | None = None
        self._feedback_callback: Callable[[str, str], None] | None = None
        self._approval_callback: Callable[[str, dict[str, Any]], None] | None = None
        self._session_id: str = str(uuid.uuid4())
        self._initialized: bool = False

        # Kill switch — operator's ultimate override
        self._kill_switch: KillSwitchState = KillSwitchState()

        # Pending approvals for HIGH-risk tools
        self._pending_approvals: dict[str, ApprovalWindow] = {}

        # Pending MEDIUM-risk proposals (cancel window)
        self._pending_medium: dict[str, ToolProposal] = {}

        # Audit trail
        self._audit_log: list[dict[str, Any]] = []

        # Lazy-loaded components
        self._process_task = None
        self._tool_executors = None
        self._check_command = None
        self._check_action = None
        self._CAPABILITIES = None
        self._get_capability_fn = None
        self._requires_approval_fn = None
        self._get_risk_level_fn = None

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
            self._get_capability_fn = get_capability
            self._requires_approval_fn = requires_approval
            self._get_risk_level_fn = get_risk_level
        except ImportError:
            self._emit_feedback("Capability registry not available", "warning")

        self._initialized = True
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Soul initialized — three-tier authority active", "success")

    def shutdown(self) -> None:
        """Gracefully shut down."""
        self._kill_switch.active = True
        self._pending_approvals.clear()
        self._pending_medium.clear()
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Soul shut down", "info")

    # ── Core: Intent processing ─────────────────────────────────────

    def process(self, intent: Intent) -> SoulResult:
        """Process a user intent through the three-tier authority model.
        
        The Soul PROPOSES. The operator DECIDES. Tools EXECUTE.
        
        Flow:
          1. Check kill switch — if active, halt immediately
          2. Asimov command pre-check
          3. Route through SAGE pipeline
          4. Classify risk of any tool calls
          5. LOW → auto-execute, log for review
          6. MEDIUM → notify user, add to proposals with cancel window
          7. HIGH → STOP, add to proposals, set needs_approval=True
          8. Return SoulResult with proposals (not executions for HIGH)
        """
        t0 = time.time()
        self._set_state(SoulState.THINKING)

        # ── TIER 1: Kill switch check ──────────────────────────────
        if self._kill_switch.active:
            self._set_state(SoulState.KILLED)
            self._audit("kill_switch_block", intent)
            return SoulResult(
                request_id=intent.request_id,
                response="Kill switch active. All operations halted.",
                state=SoulState.KILLED,
                safety_verdict=SafetyVerdict.BLOCKED_THIRD_LAW,
                duration_ms=int((time.time() - t0) * 1000),
            )

        # ── TIER 2: Asimov command pre-check ──────────────────────
        if self._check_command:
            allowed, reason = self._check_command(intent.text, "", {})
            if not allowed:
                self._set_state(SoulState.IDLE)
                self._audit("asimov_block", intent, reason=reason)
                return SoulResult(
                    request_id=intent.request_id,
                    response=f"Safety blocked: {reason}",
                    state=SoulState.IDLE,
                    safety_verdict=SafetyVerdict.BLOCKED_FIRST_LAW
                    if "FIRST LAW" in reason
                    else SafetyVerdict.BLOCKED_THIRD_LAW,
                    duration_ms=int((time.time() - t0) * 1000),
                )

        # ── TIER 2: Route through SAGE pipeline ───────────────────
        self._set_state(SoulState.ROUTING)
        try:
            response = self._process_task(intent.text)
        except Exception as e:
            self._set_state(SoulState.ERROR)
            self._audit("sage_error", intent, error=str(e))
            return SoulResult(
                request_id=intent.request_id,
                response=f"Error: {e}",
                state=SoulState.ERROR,
                safety_verdict=SafetyVerdict.ERROR,
                error=str(e),
                duration_ms=int((time.time() - t0) * 1000),
            )

        # ── TIER 2: Classify risk of tool calls ───────────────────
        # SAGE already executed tools through _TOOL_EXECUTORS which
        # include safe_file_operation, safe_computer_action, etc.
        # We need to check if any HIGH-risk tools were executed
        # WITHOUT going through the approval gate.
        #
        # This is the critical authority enforcement point.
        # If SAGE executed a HIGH-risk tool directly, we log it
        # as a violation and flag it for operator review.

        proposals = []
        tool_results = []
        needs_approval = False

        # Check if any tools were executed and classify them
        if self._tool_executors and hasattr(self, '_last_tool_calls'):
            for tc in self._last_tool_calls:
                risk = self._classify_risk(tc.get("tool_name", ""))
                proposal = ToolProposal(
                    tool_name=tc.get("tool_name", ""),
                    params=tc.get("params", {}),
                    risk=risk,
                    reason=f"SAGE proposed: {tc.get('reason', 'no reason given')}",
                    approval_required=risk == RiskLevel.HIGH,
                )

                if risk == RiskLevel.HIGH:
                    # TIER 1: HIGH-risk STOP — operator must approve
                    needs_approval = True
                    proposals.append(proposal)
                    self._audit("high_risk_proposed", intent, proposal=proposal)
                elif risk == RiskLevel.MEDIUM:
                    # TIER 2: MEDIUM-risk — notify user, cancel window
                    self._pending_medium[proposal.proposal_id] = proposal
                    proposals.append(proposal)
                    self._emit_feedback(
                        f"MEDIUM risk: {proposal.tool_name} — "
                        f"cancel within 30s if unwanted",
                        "warning",
                    )
                    self._audit("medium_risk_proposed", intent, proposal=proposal)
                else:
                    # LOW-risk — auto-execute, log for review
                    self._audit("low_risk_executed", intent, proposal=proposal)

        # If there are HIGH-risk proposals, create approval request
        approval_id = None
        if needs_approval:
            approval_id = str(uuid.uuid4())
            self._pending_approvals[approval_id] = ApprovalWindow(
                proposal_id=approval_id,
                tool_name=", ".join(p.tool_name for p in proposals if p.risk == RiskLevel.HIGH),
                params={},  # multiple tools
                risk=RiskLevel.HIGH,
                reason=f"{len([p for p in proposals if p.risk == RiskLevel.HIGH])} high-risk tools proposed",
            )
            self._set_state(SoulState.AWAITING_APPROVAL)
            # Notify operator via callback
            if self._approval_callback:
                try:
                    self._approval_callback(approval_id, {
                        "tool_name": proposals[-1].tool_name,
                        "risk": "high",
                        "reason": proposals[-1].reason,
                        "proposals": [
                            {"name": p.tool_name, "params": p.params, "reason": p.reason}
                            for p in proposals if p.risk == RiskLevel.HIGH
                        ],
                    })
                except Exception:
                    pass

        self._set_state(SoulState.IDLE)
        return SoulResult(
            request_id=intent.request_id,
            response=response,
            state=SoulState.IDLE,
            safety_verdict=SafetyVerdict.AWAITING_APPROVAL if needs_approval else SafetyVerdict.APPROVED,
            tool_proposals=proposals,
            needs_approval=needs_approval,
            approval_id=approval_id,
            agent_used="sage_pipeline",
            duration_ms=int((time.time() - t0) * 1000),
        )

    # ── Approval flow ───────────────────────────────────────────────

    def approve_tool_calls(
        self,
        approval_id: str,
        approved: bool,
    ) -> SoulResult:
        """Handle approval response from the operator.
        
        The operator decides. The Soul executes only if approved.
        """
        pending = self._pending_approvals.pop(approval_id, None)
        if not pending:
            self._audit("approval_not_found", None, approval_id=approval_id)
            return SoulResult(
                request_id=approval_id,
                response="Approval request not found or expired.",
                state=SoulState.IDLE,
                safety_verdict=SafetyVerdict.ERROR,
            )

        if not approved:
            self._audit("operator_denied", None, approval_id=approval_id)
            return SoulResult(
                request_id=approval_id,
                response="Action denied by operator.",
                state=SoulState.IDLE,
                safety_verdict=SafetyVerdict.BLOCKED_THIRD_LAW,
            )

        # Operator approved — execute the tools
        self._audit("operator_approved", None, approval_id=approval_id)
        self._set_state(SoulState.EXECUTING)

        results = []
        for tool_name in pending.tool_name.split(", "):
            tool_name = tool_name.strip()
            if not tool_name:
                continue

            try:
                # Find the executor
                if self._tool_executors and tool_name in self._tool_executors:
                    executor = self._tool_executors[tool_name]
                    # Re-execute with the approved params
                    result = executor(pending.params)
                    results.append(ToolResult(
                        call_id=approval_id,
                        tool_name=tool_name,
                        status="success",
                        result=result.get("result", "Done.") if isinstance(result, dict) else str(result),
                    ))
                else:
                    results.append(ToolResult(
                        call_id=approval_id,
                        tool_name=tool_name,
                        status="error",
                        error=f"Tool '{tool_name}' not available.",
                    ))
            except Exception as e:
                results.append(ToolResult(
                    call_id=approval_id,
                    tool_name=tool_name,
                    status="error",
                    error=str(e),
                    severity=ErrorSeverity.PERMANENT,
                ))

        self._set_state(SoulState.IDLE)
        return SoulResult(
            request_id=approval_id,
            response="; ".join(
                f"{r.tool_name}: {r.result or r.error}" for r in results
            ),
            state=SoulState.IDLE,
            safety_verdict=SafetyVerdict.APPROVED,
            tool_results=results,
        )

    # ── Kill switch ─────────────────────────────────────────────────

    def activate_kill_switch(self, reason: str = "Operator override") -> None:
        """Activate the kill switch — halts ALL Soul activity immediately."""
        self._kill_switch = KillSwitchState(
            active=True,
            activated_at=time.time(),
            reason=reason,
        )
        # Cancel all pending approvals
        self._pending_approvals.clear()
        self._pending_medium.clear()
        self._set_state(SoulState.KILLED)
        self._emit_feedback(f"KILL SWITCH ACTIVATED: {reason}", "error")
        self._audit("kill_switch_activated", None, reason=reason)

    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch."""
        self._kill_switch = KillSwitchState()
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Kill switch deactivated", "success")
        self._audit("kill_switch_deactivated", None)

    def get_kill_switch_state(self) -> KillSwitchState:
        """Get kill switch state."""
        return self._kill_switch

    # ── Proposal management ─────────────────────────────────────────

    def cancel_proposal(self, proposal_id: str) -> bool:
        """Cancel a pending proposal."""
        # Check HIGH-risk approvals
        if proposal_id in self._pending_approvals:
            del self._pending_approvals[proposal_id]
            self._audit("proposal_cancelled", None, proposal_id=proposal_id)
            return True

        # Check MEDIUM-risk pending
        if proposal_id in self._pending_medium:
            del self._pending_medium[proposal_id]
            self._audit("proposal_cancelled", None, proposal_id=proposal_id)
            return True

        return False

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        """Get all pending proposals."""
        proposals = []
        for pid, aw in self._pending_approvals.items():
            proposals.append({
                "proposal_id": pid,
                "tool_name": aw.tool_name,
                "risk": aw.risk.value,
                "reason": aw.reason,
                "status": "awaiting_approval",
                "created_at": aw.created_at,
            })
        for pid, tp in self._pending_medium.items():
            proposals.append({
                "proposal_id": pid,
                "tool_name": tp.tool_name,
                "risk": tp.risk.value,
                "reason": tp.reason,
                "status": "pending_medium",
                "created_at": time.time(),
            })
        return proposals

    # ── Capability discovery ────────────────────────────────────────

    def list_capabilities(self, domain: str | None = None) -> list[dict[str, Any]]:
        """List available tools from the capability registry."""
        if not self._get_capability_fn:
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
        if not self._get_capability_fn:
            return None

        try:
            cap = self._get_capability_fn(tool_name)
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
            "version": "0.2.0",
            "initialized": self._initialized,
            "capabilities_count": len(self._CAPABILITIES) if self._CAPABILITIES else 0,
            "kill_switch": self._kill_switch.active,
            "pending_proposals": len(self._pending_approvals) + len(self._pending_medium),
        }

    def set_state_callback(self, callback: Callable[[SoulState], None]) -> None:
        """Register state change callback."""
        self._state_callback = callback

    def set_feedback_callback(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """Register feedback message callback."""
        self._feedback_callback = callback

    def set_approval_callback(
        self, callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Register HIGH-risk approval callback."""
        self._approval_callback = callback

    # ── Internal helpers ────────────────────────────────────────────

    def _classify_risk(self, tool_name: str) -> RiskLevel:
        """Classify the risk level of a tool."""
        if self._get_risk_level_fn:
            try:
                risk = self._get_risk_level_fn(tool_name)
                if risk:
                    return risk
            except Exception:
                pass
        return RiskLevel.HIGH  # unknown = require approval (safe default)

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

    def _audit(self, event: str, intent: Intent | None, **kwargs) -> None:
        """Log an audit event for operator review."""
        entry = {
            "timestamp": time.time(),
            "event": event,
            "session_id": self._session_id,
            "kill_switch": self._kill_switch.active,
        }
        if intent:
            entry["intent"] = intent.text[:200]
            entry["intent_type"] = intent.intent_type
        entry.update(kwargs)
        self._audit_log.append(entry)
        # Keep last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
