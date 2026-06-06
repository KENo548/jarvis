"""SoulBodyProtocol — Abstract Base Class.

Three-tier control model:
  Tier 1 — YOU (operator): Approve/reject HIGH-risk; kill switch overrides everything
  Tier 2 — Soul (JARVIS): Classifies intent, plans, proposes actions
  Tier 3 — Tools/Embodiment: Only runs what cleared both above tiers

The Soul proposes. You decide. Tools execute.

Core rule: The Body NEVER directly invokes tools.
It sends Intents through this protocol. The Soul PROPOSES
what should execute. The operator APPROVES what actually runs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from .types import Intent, SoulResult, ToolCall, ToolResult, SoulState, KillSwitchState


class SoulBodyProtocol(ABC):
    """Contract between Soul (JARVIS) and Body (Mark XXXIX).
    
    The Body calls these methods. The Soul implements them.
    
    Authority hierarchy:
      1. Operator (YOU) — has final authority, kill switch, HIGH-risk approval
      2. Soul (JARVIS) — has intelligence, classifies, routes, PROPOSES
      3. Tools — only runs what cleared both above tiers
    """

    # ── Core: Intent processing ─────────────────────────────────────

    @abstractmethod
    def process(self, intent: Intent) -> SoulResult:
        """Process a user intent and PROPOSE tool executions.
        
        The implementation MUST:
        1. Check kill switch — if active, return immediately
        2. Run Asimov command pre-check
        3. Classify intent and route to appropriate agent
        4. For each tool call, classify risk level
        5. LOW-risk → auto-execute, log for review
        6. MEDIUM-risk → notify user, add to proposals with cancel window
        7. HIGH-risk → STOP, add to proposals, set needs_approval=True
        8. Return SoulResult with proposals (not executions for HIGH)
        
        The Soul PROPOSES. The operator DECIDES. Tools EXECUTE.
        
        Args:
            intent: Structured user request from the Body
            
        Returns:
            SoulResult with response, tool proposals, safety verdict
        """
        ...

    # ── Approval flow ───────────────────────────────────────────────

    @abstractmethod
    def approve_tool_calls(
        self,
        approval_id: str,
        approved: bool,
    ) -> SoulResult:
        """Respond to an approval request from the operator.
        
        When a HIGH-risk tool is proposed, the Soul returns
        a SoulResult with needs_approval=True. The Body shows
        a dialog. When the operator decides, the Body calls this method.
        
        Args:
            approval_id: The approval token from the original SoulResult
            approved: True if operator approved, False if denied
            
        Returns:
            SoulResult with the execution result (or denial message)
        """
        ...

    # ── Kill switch ─────────────────────────────────────────────────

    @abstractmethod
    def activate_kill_switch(self, reason: str = "Operator override") -> None:
        """Activate the kill switch — halts ALL Soul activity immediately.
        
        This is the operator's ultimate override. When active:
        - No tool can run (even if previously approved)
        - No new intents are processed
        - All pending approvals are cancelled
        - The Soul enters KILLED state
        
        Args:
            reason: Why the kill switch was activated
        """
        ...

    @abstractmethod
    def deactivate_kill_switch(self) -> None:
        """Deactivate the kill switch and return to normal operation."""
        ...

    @abstractmethod
    def get_kill_switch_state(self) -> KillSwitchState:
        """Get the current kill switch state."""
        ...

    # ── Proposal management ─────────────────────────────────────────

    @abstractmethod
    def cancel_proposal(self, proposal_id: str) -> bool:
        """Cancel a pending proposal (MEDIUM or HIGH risk).
        
        The operator can cancel any proposal before it executes.
        For MEDIUM-risk, this cancels the cancel window.
        For HIGH-risk, this denies the approval request.
        
        Args:
            proposal_id: The proposal to cancel
            
        Returns:
            True if cancelled, False if not found or already executed
        """
        ...

    @abstractmethod
    def get_pending_proposals(self) -> list[dict[str, Any]]:
        """Get all pending proposals awaiting decision.
        
        Returns:
            List of proposal dicts with keys:
            proposal_id, tool_name, params, risk, reason, status
        """
        ...

    # ── Capability discovery ────────────────────────────────────────

    @abstractmethod
    def list_capabilities(self, domain: str | None = None) -> list[dict[str, Any]]:
        """Discover available tools and their risk profiles.
        
        The Body uses this to:
        - Populate UI tool menus
        - Show risk indicators before execution
        - Filter by domain (e.g., "browser", "files")
        
        Returns:
            List of capability dicts with keys:
            name, domain, risk, approval_required, description
        """
        ...

    @abstractmethod
    def get_capability(self, tool_name: str) -> dict[str, Any] | None:
        """Get metadata for a single tool."""
        ...

    # ── Status & feedback ───────────────────────────────────────────

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get Soul status for the HUD.
        
        Returns dict with keys:
        - "state": SoulState value
        - "session_id": str
        - "version": str
        - "capabilities_count": int
        - "kill_switch": bool
        - "pending_proposals": int
        """
        ...

    @abstractmethod
    def set_state_callback(self, callback: Callable[[SoulState], None]) -> None:
        """Register a callback for state changes."""
        ...

    @abstractmethod
    def set_feedback_callback(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """Register a callback for feedback messages."""
        ...

    @abstractmethod
    def set_approval_callback(
        self, callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Register a callback for HIGH-risk approval requests.
        
        When a HIGH-risk tool is proposed, the Soul calls this
        to notify the Body, which shows the approval dialog.
        
        Args:
            callback: Function that receives (proposal_id, proposal_details)
        """
        ...

    # ── Lifecycle ───────────────────────────────────────────────────

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the Soul (load models, connect to memory, etc.)."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully shut down the Soul."""
        ...
