"""JarvisSoul — JARVIS implementation of the SoulBodyProtocol.

Three-tier control model enforced:
  Tier 1 — Operator: kill switch, HIGH-risk approval, can override anything
  Tier 2 — Soul: classifies intent, plans, proposes actions
  Tier 3 — Tools: only runs what cleared both above tiers

The Soul proposes. The operator decides. Tools execute.

─ What changed from v0.2.0 ──────────────────────────────────────────────────

Bug 1 (CRITICAL): SAGE was executing tools BEFORE the approval gate.
  Fix: GatedExecutorMap wraps _TOOL_EXECUTORS. Every tool call is intercepted
       BEFORE execution. HIGH-risk calls raise AwaitingApproval instead of
       running. LOW/MEDIUM calls are logged and then allowed through.

Bug 2 (CRITICAL): _last_tool_calls never existed — the risk classification
       block was dead code. The gate makes it unnecessary; interception
       happens at the executor level, not after the fact.

Bug 3 (STRUCTURAL): MEDIUM-risk had no actual cancel window — just a message.
  Fix: MediumRiskTimer starts a real daemon thread per proposal. After
       MEDIUM_CANCEL_WINDOW_SECONDS (default 20s), it fires the executor
       only if the proposal hasn't been cancelled.

Bug 4 (STRUCTURAL): approve_tool_calls re-executed with params={}.
  Fix: ApprovalWindow now stores the full (tool_name, executor, params) tuple.
       On approval, we re-fire with the original params.

──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable

from protocols.types import (
    ApprovalStatus,
    ApprovalWindow,
    ErrorSeverity,
    Intent,
    KillSwitchState,
    RiskLevel,
    SafetyVerdict,
    SoulResult,
    SoulState,
    ToolCall,
    ToolProposal,
    ToolResult,
)
from protocols.soul_body import SoulBodyProtocol

# How long the operator has to cancel a MEDIUM-risk action before it fires.
MEDIUM_CANCEL_WINDOW_SECONDS: int = 20

# How long a HIGH-risk approval request stays open before expiring.
HIGH_APPROVAL_TIMEOUT_SECONDS: int = 300  # 5 minutes


# ── Exceptions ─────────────────────────────────────────────────────────────

class AwaitingApproval(Exception):
    """Raised by the gated executor when a HIGH-risk tool is intercepted.

    Carries the full context needed to resume execution if the operator
    approves. Raising instead of returning keeps sage.py's tool dispatch
    loop ignorant of the approval concept — the Soul handles it entirely.
    """
    def __init__(self, tool_name: str, params: dict, executor: Callable):
        self.tool_name = tool_name
        self.params = params
        self.executor = executor
        super().__init__(f"HIGH-risk tool '{tool_name}' requires operator approval")


class KillSwitchActive(Exception):
    """Raised by the gated executor when the kill switch is active."""


# ── Gated executor map ─────────────────────────────────────────────────────

class GatedExecutorMap:
    """Wraps _TOOL_EXECUTORS and enforces the three-tier authority model.

    This is the enforcement point — every tool call passes through here
    before any executor fires. The Soul injects this over sage.py's
    _TOOL_EXECUTORS at initialization so SAGE's dispatch loop is
    transparently gated.

    LOW-risk  → execute immediately, audit log entry created.
    MEDIUM-risk → start cancel-window timer; execute after window unless cancelled.
    HIGH-risk → raise AwaitingApproval (never executes without operator yes).
    Kill switch → raise KillSwitchActive (nothing executes).
    """

    def __init__(
        self,
        raw_executors: dict[str, Callable],
        classify_risk: Callable[[str], RiskLevel],
        get_kill_switch: Callable[[], KillSwitchState],
        on_low: Callable[[str, dict, Any], None],
        on_medium: Callable[[str, dict, Callable], None],
        on_high: Callable[[str, dict, Callable], None],
    ):
        self._raw = raw_executors
        self._classify_risk = classify_risk
        self._get_kill_switch = get_kill_switch
        self._on_low = on_low
        self._on_medium = on_medium
        self._on_high = on_high

    # Make it behave like a dict so sage.py's `executor = _TOOL_EXECUTORS.get(name)` works.
    def get(self, tool_name: str, default=None) -> Callable | None:
        raw = self._raw.get(tool_name, default)
        if raw is None:
            return None
        return self._wrap(tool_name, raw)

    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._raw

    def _wrap(self, tool_name: str, raw_executor: Callable) -> Callable:
        """Return a wrapped callable that enforces the gate."""
        def gated(params: dict) -> Any:
            # ── Kill switch: blocks everything ──────────────────────
            ks = self._get_kill_switch()
            if ks.active:
                raise KillSwitchActive(
                    f"Kill switch active (reason: {ks.reason}). "
                    f"Tool '{tool_name}' blocked."
                )

            risk = self._classify_risk(tool_name)

            if risk == RiskLevel.LOW:
                result = raw_executor(params)
                self._on_low(tool_name, params, result)
                return result

            elif risk == RiskLevel.MEDIUM:
                # Don't execute yet — hand off to the cancel-window handler.
                # The handler will either fire after the window or do nothing
                # if the proposal is cancelled. We return a placeholder so
                # SAGE's loop can continue building the response text.
                self._on_medium(tool_name, params, raw_executor)
                return {
                    "tool": tool_name,
                    "status": "pending_medium",
                    "result": (
                        f"[{tool_name}] queued — you have {MEDIUM_CANCEL_WINDOW_SECONDS}s "
                        f"to cancel. Use /cancel <id> to stop it."
                    ),
                }

            else:  # HIGH — never executes without explicit approval
                self._on_high(tool_name, params, raw_executor)
                raise AwaitingApproval(tool_name, params, raw_executor)

        return gated


# ── Medium-risk cancel window ───────────────────────────────────────────────

class MediumRiskTimer:
    """Fires a tool executor after a cancel window unless cancelled first.

    One instance per MEDIUM-risk proposal. The thread is a daemon so it
    never prevents process exit. If the kill switch activates before the
    timer fires, the execution is silently dropped.
    """

    def __init__(
        self,
        proposal_id: str,
        tool_name: str,
        params: dict,
        executor: Callable,
        delay_seconds: int,
        get_kill_switch: Callable[[], KillSwitchState],
        on_fired: Callable[[str, str, Any], None],
        on_cancelled: Callable[[str], None],
    ):
        self.proposal_id = proposal_id
        self._cancelled = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            args=(tool_name, params, executor, delay_seconds,
                  get_kill_switch, on_fired, on_cancelled),
            daemon=True,
            name=f"medium-risk-{proposal_id[:8]}",
        )

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancelled.set()

    def _run(self, tool_name, params, executor, delay, get_kill_switch, on_fired, on_cancelled):
        cancelled = self._cancelled.wait(timeout=delay)
        if cancelled:
            on_cancelled(self.proposal_id)
            return
        if get_kill_switch().active:
            on_cancelled(self.proposal_id)
            return
        try:
            result = executor(params)
            on_fired(self.proposal_id, tool_name, result)
        except Exception as e:
            on_fired(self.proposal_id, tool_name, {"error": str(e)})


# ── JarvisSoul ─────────────────────────────────────────────────────────────

class JarvisSoul(SoulBodyProtocol):
    """JARVIS implementation of the Soul-Body protocol.

    Authority model:
      1. Operator has final authority — kill switch, HIGH-risk approval.
      2. Soul has intelligence — classifies, routes, proposes.
      3. Tools have execution — only runs what cleared both tiers.

    The Soul NEVER overrides the operator. Ever.
    """

    VERSION = "0.3.0"

    def __init__(self):
        self._state: SoulState = SoulState.IDLE
        self._state_callback: Callable[[SoulState], None] | None = None
        self._feedback_callback: Callable[[str, str], None] | None = None
        self._approval_callback: Callable[[str, dict[str, Any]], None] | None = None
        self._session_id: str = str(uuid.uuid4())
        self._initialized: bool = False

        # Operator's ultimate override
        self._kill_switch: KillSwitchState = KillSwitchState()

        # HIGH-risk: waiting for operator yes/no
        # key: approval_id → (ApprovalWindow, executor_callable, params)
        self._pending_approvals: dict[str, tuple[ApprovalWindow, Callable, dict]] = {}

        # MEDIUM-risk: cancel-window timers
        # key: proposal_id → MediumRiskTimer
        self._pending_medium: dict[str, MediumRiskTimer] = {}

        # Audit trail (in-memory, last 1000 entries)
        self._audit_log: list[dict[str, Any]] = []

        # Lock for shared state touched by timer threads
        self._lock = threading.Lock()

        # Lazy-loaded SAGE components
        self._process_task: Callable | None = None
        self._raw_tool_executors: dict[str, Callable] | None = None
        self._gated_executors: GatedExecutorMap | None = None
        self._check_command: Callable | None = None
        self._CAPABILITIES: dict | None = None
        self._get_capability_fn: Callable | None = None
        self._get_risk_level_fn: Callable | None = None

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Initialize the Soul — load SAGE pipeline and install the gate."""
        if self._initialized:
            return

        self._set_state(SoulState.THINKING)

        # 1. Load SAGE pipeline
        try:
            import sage as _sage
            self._process_task = _sage.process_task
            self._raw_tool_executors = _sage._TOOL_EXECUTORS

            # ── Install the gate ──────────────────────────────────────────
            # Replace sage's executor map with our gated version.
            # sage.py's dispatch does: executor = _TOOL_EXECUTORS.get(tool_name)
            # After this assignment, every tool lookup goes through the gate.
            self._gated_executors = GatedExecutorMap(
                raw_executors=self._raw_tool_executors,
                classify_risk=self._classify_risk,
                get_kill_switch=lambda: self._kill_switch,
                on_low=self._handle_low_risk,
                on_medium=self._handle_medium_risk,
                on_high=self._handle_high_risk_intercept,
            )
            _sage._TOOL_EXECUTORS = self._gated_executors
            # ─────────────────────────────────────────────────────────────

        except ImportError as e:
            self._emit_feedback(f"Failed to load SAGE pipeline: {e}", "error")
            raise

        # 2. Asimov safety layer
        try:
            from tools.asimov import check_command, check_action
            self._check_command = check_command
        except ImportError:
            self._emit_feedback("Asimov safety layer not available — proceeding without pre-check", "warning")

        # 3. Capability registry
        try:
            from tools.embodiment.capability_registry import (
                CAPABILITIES,
                get_capability,
                get_risk_level,
            )
            self._CAPABILITIES = CAPABILITIES
            self._get_capability_fn = get_capability
            self._get_risk_level_fn = get_risk_level
        except ImportError:
            self._emit_feedback("Capability registry not available — all tools default to HIGH risk", "warning")

        self._initialized = True
        self._set_state(SoulState.IDLE)
        self._emit_feedback(
            f"Soul v{self.VERSION} initialized — three-tier authority active, gate installed",
            "success",
        )

    def shutdown(self) -> None:
        """Gracefully shut down — cancel all pending actions."""
        with self._lock:
            for timer in self._pending_medium.values():
                timer.cancel()
            self._pending_medium.clear()
            self._pending_approvals.clear()
        self._kill_switch.active = True
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Soul shut down", "info")

    # ── Core: Intent processing ─────────────────────────────────────────────

    def process(self, intent: Intent) -> SoulResult:
        """Process a user intent through the three-tier authority model.

        The Soul PROPOSES. The operator DECIDES. Tools EXECUTE.

        Flow:
          1. Kill switch check — halt immediately if active.
          2. Asimov command pre-check — block harmful commands.
          3. Route through SAGE pipeline — the gate intercepts tool calls.
             LOW-risk tools execute during this step (they're safe).
             MEDIUM-risk tools are queued with a cancel window.
             HIGH-risk tools raise AwaitingApproval — SAGE gets an error,
             which we catch and convert to a needs_approval response.
          4. Return SoulResult with full state for the Body to render.
        """
        t0 = time.time()
        self._set_state(SoulState.THINKING)

        # Thread-local storage for tool calls intercepted during this request.
        # The gate callbacks write here; we read after process_task returns.
        intercepted_high: list[dict] = []
        intercepted_medium: list[dict] = []
        intercepted_low: list[dict] = []

        # Temporarily wire callbacks to capture this request's tool calls.
        # We save and restore so concurrent calls don't cross-contaminate.
        # (Single-user desktop app, but belt-and-suspenders.)
        original_low = self._handle_low_risk
        original_medium = self._handle_medium_risk
        original_high = self._handle_high_risk_intercept

        def capture_low(tool_name, params, result):
            intercepted_low.append({"tool_name": tool_name, "params": params, "result": result})
            original_low(tool_name, params, result)

        def capture_medium(tool_name, params, executor):
            intercepted_medium.append({"tool_name": tool_name, "params": params})
            original_medium(tool_name, params, executor)

        def capture_high(tool_name, params, executor):
            intercepted_high.append({"tool_name": tool_name, "params": params, "executor": executor})
            # Don't call original_high — it would double-register.
            # AwaitingApproval will be raised by the gate immediately after.

        # Patch gate callbacks for this request
        if self._gated_executors:
            self._gated_executors._on_low = capture_low
            self._gated_executors._on_medium = capture_medium
            self._gated_executors._on_high = capture_high

        try:
            return self._process_intent(intent, t0, intercepted_high, intercepted_medium, intercepted_low)
        finally:
            # Restore callbacks
            if self._gated_executors:
                self._gated_executors._on_low = original_low
                self._gated_executors._on_medium = original_medium
                self._gated_executors._on_high = original_high

    def _process_intent(
        self,
        intent: Intent,
        t0: float,
        intercepted_high: list,
        intercepted_medium: list,
        intercepted_low: list,
    ) -> SoulResult:

        # ── TIER 1: Kill switch ──────────────────────────────────────────
        if self._kill_switch.active:
            self._set_state(SoulState.KILLED)
            self._audit("kill_switch_block", intent)
            return SoulResult(
                request_id=intent.request_id,
                response="Kill switch active. All operations halted. Use /resume to deactivate.",
                state=SoulState.KILLED,
                safety_verdict=SafetyVerdict.BLOCKED_THIRD_LAW,
                duration_ms=self._ms(t0),
            )

        # ── TIER 2: Asimov command pre-check ────────────────────────────
        if self._check_command:
            allowed, reason = self._check_command(intent.text, "", {})
            if not allowed:
                self._set_state(SoulState.IDLE)
                self._audit("asimov_block", intent, reason=reason)
                return SoulResult(
                    request_id=intent.request_id,
                    response=f"Safety blocked: {reason}",
                    state=SoulState.IDLE,
                    safety_verdict=(
                        SafetyVerdict.BLOCKED_FIRST_LAW
                        if "FIRST LAW" in reason
                        else SafetyVerdict.BLOCKED_THIRD_LAW
                    ),
                    duration_ms=self._ms(t0),
                )

        # ── TIER 2: Route through SAGE (gate intercepts tool calls) ─────
        self._set_state(SoulState.ROUTING)
        awaiting: AwaitingApproval | None = None
        response_text = ""

        try:
            response_text = self._process_task(intent.text)
        except AwaitingApproval as e:
            # A HIGH-risk tool was intercepted before it could execute.
            # SAGE's loop is interrupted; we handle the rest here.
            awaiting = e
            response_text = (
                f"I need your approval before running **{e.tool_name}** (HIGH risk). "
                f"This is a state-changing action. Approve or deny below."
            )
        except Exception as e:
            self._set_state(SoulState.ERROR)
            self._audit("sage_error", intent, error=str(e))
            return SoulResult(
                request_id=intent.request_id,
                response=f"Error in SAGE pipeline: {e}",
                state=SoulState.ERROR,
                safety_verdict=SafetyVerdict.ERROR,
                error=str(e),
                duration_ms=self._ms(t0),
            )

        # ── Build proposals from intercepted tool calls ─────────────────
        proposals: list[ToolProposal] = []
        needs_approval = False
        approval_id: str | None = None

        # LOW-risk: already executed, just log them
        for item in intercepted_low:
            self._audit("low_risk_executed", intent, tool=item["tool_name"])

        # MEDIUM-risk: timers already started by capture_medium → original_medium
        for item in intercepted_medium:
            proposals.append(ToolProposal(
                tool_name=item["tool_name"],
                params=item["params"],
                risk=RiskLevel.MEDIUM,
                reason=f"MEDIUM-risk action queued — fires in {MEDIUM_CANCEL_WINDOW_SECONDS}s unless cancelled",
                approval_required=False,
            ))

        # HIGH-risk: either from AwaitingApproval or from intercepted_high
        high_items = intercepted_high[:]
        if awaiting:
            high_items.append({
                "tool_name": awaiting.tool_name,
                "params": awaiting.params,
                "executor": awaiting.executor,
            })

        if high_items:
            needs_approval = True
            approval_id = str(uuid.uuid4())
            self._set_state(SoulState.AWAITING_APPROVAL)

            # Store approval context — full executor + params so we can re-fire on approval
            with self._lock:
                for item in high_items:
                    per_tool_id = str(uuid.uuid4())
                    window = ApprovalWindow(
                        proposal_id=per_tool_id,
                        tool_name=item["tool_name"],
                        params=item["params"],
                        risk=RiskLevel.HIGH,
                        reason=f"HIGH-risk: {item['tool_name']} requires explicit operator approval",
                        timeout_seconds=HIGH_APPROVAL_TIMEOUT_SECONDS,
                    )
                    self._pending_approvals[approval_id] = (window, item["executor"], item["params"])
                    proposals.append(ToolProposal(
                        tool_name=item["tool_name"],
                        params=item["params"],
                        risk=RiskLevel.HIGH,
                        reason=window.reason,
                        approval_required=True,
                        safety_verdict=SafetyVerdict.AWAITING_APPROVAL,
                        call_id=per_tool_id,
                    ))
                    self._audit("high_risk_proposed", intent, tool=item["tool_name"], approval_id=approval_id)

            # Notify Body — it shows the approval dialog
            if self._approval_callback:
                try:
                    self._approval_callback(approval_id, {
                        "tools": [
                            {"name": i["tool_name"], "params": i["params"]}
                            for i in high_items
                        ],
                        "count": len(high_items),
                        "timeout_seconds": HIGH_APPROVAL_TIMEOUT_SECONDS,
                    })
                except Exception:
                    pass

        final_state = SoulState.AWAITING_APPROVAL if needs_approval else SoulState.IDLE
        self._set_state(final_state)

        return SoulResult(
            request_id=intent.request_id,
            response=response_text,
            state=final_state,
            safety_verdict=SafetyVerdict.AWAITING_APPROVAL if needs_approval else SafetyVerdict.APPROVED,
            tool_proposals=proposals,
            needs_approval=needs_approval,
            approval_id=approval_id,
            agent_used="sage_pipeline",
            duration_ms=self._ms(t0),
        )

    # ── Approval flow ────────────────────────────────────────────────────────

    def approve_tool_calls(self, approval_id: str, approved: bool) -> SoulResult:
        """Handle the operator's approval decision for a HIGH-risk proposal."""
        with self._lock:
            pending = self._pending_approvals.pop(approval_id, None)

        if not pending:
            self._audit("approval_not_found", None, approval_id=approval_id)
            return SoulResult(
                request_id=approval_id,
                response="Approval request not found or expired.",
                state=SoulState.IDLE,
                safety_verdict=SafetyVerdict.ERROR,
            )

        window, executor, params = pending

        if not approved:
            self._audit("operator_denied", None, approval_id=approval_id, tool=window.tool_name)
            return SoulResult(
                request_id=approval_id,
                response=f"**{window.tool_name}** denied by operator. Action not taken.",
                state=SoulState.IDLE,
                safety_verdict=SafetyVerdict.BLOCKED_THIRD_LAW,
            )

        # Operator approved — check kill switch one last time before firing
        if self._kill_switch.active:
            self._audit("kill_switch_blocked_approved_tool", None, tool=window.tool_name)
            return SoulResult(
                request_id=approval_id,
                response="Kill switch activated after approval — action blocked.",
                state=SoulState.KILLED,
                safety_verdict=SafetyVerdict.BLOCKED_THIRD_LAW,
            )

        self._set_state(SoulState.EXECUTING)
        self._audit("operator_approved", None, approval_id=approval_id, tool=window.tool_name)

        try:
            # Fire with the original params captured at intercept time
            result = executor(params)
            result_text = (
                result.get("result", "Done.")
                if isinstance(result, dict)
                else str(result)
            )
            tool_result = ToolResult(
                call_id=approval_id,
                tool_name=window.tool_name,
                status="success",
                result=result_text,
            )
            self._audit("high_risk_executed", None, tool=window.tool_name, result=result_text)
        except Exception as e:
            tool_result = ToolResult(
                call_id=approval_id,
                tool_name=window.tool_name,
                status="error",
                error=str(e),
                severity=ErrorSeverity.PERMANENT,
            )
            self._audit("high_risk_error", None, tool=window.tool_name, error=str(e))

        self._set_state(SoulState.IDLE)
        return SoulResult(
            request_id=approval_id,
            response=f"**{window.tool_name}**: {tool_result.result or tool_result.error}",
            state=SoulState.IDLE,
            safety_verdict=SafetyVerdict.APPROVED,
            tool_results=[tool_result],
        )

    # ── Kill switch ──────────────────────────────────────────────────────────

    def activate_kill_switch(self, reason: str = "Operator override") -> None:
        """Activate the kill switch — halts ALL activity immediately.

        Cancels all pending MEDIUM timers and clears all HIGH approvals.
        Even tools currently in the middle of execution will be blocked
        if they check the gate again (most long-running tools do).
        """
        self._kill_switch = KillSwitchState(
            active=True,
            activated_at=time.time(),
            reason=reason,
        )
        # Cancel all MEDIUM timers immediately
        with self._lock:
            for timer in self._pending_medium.values():
                timer.cancel()
            self._pending_medium.clear()
            self._pending_approvals.clear()

        self._set_state(SoulState.KILLED)
        self._emit_feedback(f"KILL SWITCH ACTIVATED: {reason}", "error")
        self._audit("kill_switch_activated", None, reason=reason)

    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch and return to IDLE."""
        self._kill_switch = KillSwitchState()
        self._set_state(SoulState.IDLE)
        self._emit_feedback("Kill switch deactivated — Soul resuming", "success")
        self._audit("kill_switch_deactivated", None)

    def get_kill_switch_state(self) -> KillSwitchState:
        return self._kill_switch

    # ── Proposal management ──────────────────────────────────────────────────

    def cancel_proposal(self, proposal_id: str) -> bool:
        """Cancel a pending proposal before it executes."""
        with self._lock:
            # HIGH-risk approval
            if proposal_id in self._pending_approvals:
                del self._pending_approvals[proposal_id]
                self._audit("proposal_cancelled", None, proposal_id=proposal_id, risk="high")
                return True

            # MEDIUM-risk timer
            if proposal_id in self._pending_medium:
                timer = self._pending_medium.pop(proposal_id)
                timer.cancel()
                self._audit("proposal_cancelled", None, proposal_id=proposal_id, risk="medium")
                self._emit_feedback(f"Cancelled medium-risk action {proposal_id[:8]}", "info")
                return True

        return False

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        """Get all pending proposals awaiting decision."""
        proposals = []
        with self._lock:
            for aid, (window, _, _) in self._pending_approvals.items():
                proposals.append({
                    "proposal_id": aid,
                    "tool_name": window.tool_name,
                    "risk": "high",
                    "reason": window.reason,
                    "status": "awaiting_approval",
                    "created_at": window.created_at,
                    "timeout_seconds": window.timeout_seconds,
                    "expires_in": max(0, window.timeout_seconds - (time.time() - window.created_at)),
                })
            for pid in self._pending_medium:
                proposals.append({
                    "proposal_id": pid,
                    "risk": "medium",
                    "status": "pending_cancel_window",
                })
        return proposals

    # ── Capability discovery ─────────────────────────────────────────────────

    def list_capabilities(self, domain: str | None = None) -> list[dict[str, Any]]:
        """List available tools and their risk profiles."""
        if not self._get_capability_fn:
            return []
        try:
            from tools.embodiment.capability_registry import list_capabilities as _list
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
                for c in _list(domain)
            ]
        except ImportError:
            return []

    def get_capability(self, tool_name: str) -> dict[str, Any] | None:
        """Get metadata for a single tool."""
        if not self._get_capability_fn:
            return None
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

    # ── Status & feedback ─────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get Soul status for the HUD."""
        with self._lock:
            pending_high = len(self._pending_approvals)
            pending_medium = len(self._pending_medium)
        return {
            "state": self._state.value,
            "session_id": self._session_id,
            "version": self.VERSION,
            "initialized": self._initialized,
            "capabilities_count": len(self._CAPABILITIES) if self._CAPABILITIES else 0,
            "kill_switch": self._kill_switch.active,
            "kill_switch_reason": self._kill_switch.reason if self._kill_switch.active else None,
            "pending_high_risk": pending_high,
            "pending_medium_risk": pending_medium,
            "pending_proposals": pending_high + pending_medium,
            "gate_installed": self._gated_executors is not None,
        }

    def set_state_callback(self, cb: Callable[[SoulState], None]) -> None:
        self._state_callback = cb

    def set_feedback_callback(self, cb: Callable[[str, str], None]) -> None:
        self._feedback_callback = cb

    def set_approval_callback(self, cb: Callable[[str, dict[str, Any]], None]) -> None:
        self._approval_callback = cb

    # ── Gate callbacks ────────────────────────────────────────────────────────

    def _handle_low_risk(self, tool_name: str, params: dict, result: Any) -> None:
        """Called by gate after a LOW-risk tool executes successfully."""
        self._emit_feedback(f"OK {tool_name} executed (low risk)", "info")
        self._audit("low_risk_executed", None, tool=tool_name)

    def _handle_medium_risk(self, tool_name: str, params: dict, executor: Callable) -> None:
        """Called by gate when a MEDIUM-risk tool is intercepted.

        Starts a cancel-window timer. The tool fires after MEDIUM_CANCEL_WINDOW_SECONDS
        unless the operator calls cancel_proposal(proposal_id).
        """
        proposal_id = str(uuid.uuid4())
        timer = MediumRiskTimer(
            proposal_id=proposal_id,
            tool_name=tool_name,
            params=params,
            executor=executor,
            delay_seconds=MEDIUM_CANCEL_WINDOW_SECONDS,
            get_kill_switch=lambda: self._kill_switch,
            on_fired=self._on_medium_fired,
            on_cancelled=self._on_medium_cancelled,
        )
        with self._lock:
            self._pending_medium[proposal_id] = timer
        timer.start()

        self._emit_feedback(
            f"MEDIUM risk: {tool_name} queued — "
            f"fires in {MEDIUM_CANCEL_WINDOW_SECONDS}s. "
            f"Cancel ID: {proposal_id[:8]}",
            "warning",
        )
        self._audit("medium_risk_queued", None, tool=tool_name, proposal_id=proposal_id)

    def _handle_high_risk_intercept(self, tool_name: str, params: dict, executor: Callable) -> None:
        """Called by gate when a HIGH-risk tool is intercepted.

        The gate will raise AwaitingApproval immediately after this callback.
        This method is intentionally a no-op here because _process_intent
        handles registration via the capture_high local function.
        The gate's raise ensures SAGE's loop never reaches the executor.
        """
        # Registration happens in _process_intent via capture_high + high_items.
        # This callback exists so the GatedExecutorMap interface is consistent.
        pass

    def _on_medium_fired(self, proposal_id: str, tool_name: str, result: Any) -> None:
        """Timer callback when a MEDIUM-risk action fires after the cancel window."""
        with self._lock:
            self._pending_medium.pop(proposal_id, None)
        result_text = result.get("result", str(result)) if isinstance(result, dict) else str(result)
        self._emit_feedback(f"OK {tool_name} executed after cancel window: {result_text}", "success")
        self._audit("medium_risk_executed", None, tool=tool_name, proposal_id=proposal_id)

    def _on_medium_cancelled(self, proposal_id: str) -> None:
        """Timer callback when a MEDIUM-risk action is cancelled or kill-switched."""
        with self._lock:
            self._pending_medium.pop(proposal_id, None)
        self._audit("medium_risk_cancelled", None, proposal_id=proposal_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _classify_risk(self, tool_name: str) -> RiskLevel:
        """Classify the risk level of a tool. Unknown = HIGH (safe default)."""
        if self._get_risk_level_fn:
            try:
                risk = self._get_risk_level_fn(tool_name)
                if risk is not None:
                    return risk
            except Exception:
                pass
        return RiskLevel.HIGH

    def _set_state(self, state: SoulState) -> None:
        self._state = state
        if self._state_callback:
            try:
                self._state_callback(state)
            except Exception:
                pass

    def _emit_feedback(self, message: str, level: str = "info") -> None:
        if self._feedback_callback:
            try:
                self._feedback_callback(message, level)
            except Exception:
                pass

    def _audit(self, event: str, intent: Intent | None, **kwargs) -> None:
        entry: dict[str, Any] = {
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
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    @staticmethod
    def _ms(t0: float) -> int:
        return int((time.time() - t0) * 1000)
