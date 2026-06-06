"""SoulBodyProtocol — Abstract Base Class.

The Body (Mark XXXIX) calls these methods.
The Soul (JARVIS) implements them.

Core rule: The Body NEVER directly invokes tools.
It sends Intents through this protocol. The Soul decides
what executes, at what risk level, with what approval requirement.
The Body just renders the result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from .types import Intent, SoulResult, ToolCall, ToolResult, SoulState


class SoulBodyProtocol(ABC):
    """Contract between Soul (JARVIS) and Body (Mark XXXIX).
    
    The Body calls these methods. The Soul implements them.
    All tool execution MUST go through process() — 
    the implementation enforces the safety gate.
    """

    # ── Core: Intent processing ─────────────────────────────────────

    @abstractmethod
    def process(self, intent: Intent) -> SoulResult:
        """Process a user intent through the full soul pipeline.
        
        The implementation MUST:
        1. Run Asimov command pre-check
        2. Route to the appropriate agent
        3. For each tool call, run Asimov action check + risk assessment
        4. Execute tools (or return AWAITING_APPROVAL for HIGH-risk)
        5. Assemble and return SoulResult
        
        Args:
            intent: Structured user request from the Body
            
        Returns:
            SoulResult with response, tool calls, safety verdict
        """
        ...

    # ── Approval flow ───────────────────────────────────────────────

    @abstractmethod
    def approve_tool_calls(
        self,
        approval_id: str,
        approved: bool,
    ) -> SoulResult:
        """Respond to an approval request from the Soul.
        
        When a HIGH-risk tool is encountered, the Soul returns
        a SoulResult with needs_approval=True. The Body shows
        a dialog. When the user decides, the Body calls this method.
        
        Args:
            approval_id: The approval token from the original SoulResult
            approved: True if user approved, False if denied
            
        Returns:
            SoulResult with the execution result (or denial message)
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
        - "state": SoulState value (idle, listening, thinking, etc.)
        - "session_id": str
        - "version": str
        - "capabilities_count": int
        """
        ...

    @abstractmethod
    def set_state_callback(self, callback: Callable[[SoulState], None]) -> None:
        """Register a callback for state changes.
        
        The Soul calls this whenever its state changes,
        so the Body can update the HUD in real time.
        
        Args:
            callback: Function that receives SoulState updates
        """
        ...

    @abstractmethod
    def set_feedback_callback(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """Register a callback for feedback messages.
        
        The Soul calls this to send info/warning/error messages
        to the Body's HUD.
        
        Args:
            callback: Function that receives (message, level) tuples
                      level is "info" | "warning" | "error" | "success"
        """
        ...

    # ── Lifecycle ───────────────────────────────────────────────────

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the Soul (load models, connect to memory, etc.).
        
        Called once at startup before any intents are processed.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully shut down the Soul.
        
        Called when the Body is closing.
        """
        ...
