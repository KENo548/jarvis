"""Data types for the SoulBodyProtocol contract.

Three-tier control model:
  Tier 1 — YOU (operator): Approve/reject HIGH-risk; kill switch overrides everything
  Tier 2 — Soul (JARVIS): Classifies intent, plans, proposes actions
  Tier 3 — Tools/Embodiment: Only runs what cleared both above tiers

The Soul proposes. You decide. Tools execute.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SafetyVerdict(Enum):
    """Outcome of the Asimov safety check."""
    APPROVED = "approved"
    BLOCKED_FIRST_LAW = "blocked_first_law"
    BLOCKED_THIRD_LAW = "blocked_third_law"
    AWAITING_APPROVAL = "awaiting_approval"
    ERROR = "error"


class RiskLevel(Enum):
    """Risk classification for tool execution.
    
    LOW    → Soul auto-executes, logs for later review
    MEDIUM → Soul notifies user, executes after cancel window
    HIGH   → Soul stops, shows what/why, waits for explicit yes
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ErrorSeverity(Enum):
    """Severity of an execution error."""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    CRITICAL = "critical"


class SoulState(Enum):
    """Current state of the soul for HUD display."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ROUTING = "routing"
    PROPOSING = "proposing"       # Soul is generating tool proposals
    AWAITING_APPROVAL = "awaiting_approval"  # HIGH-risk waiting for user
    EXECUTING = "executing"
    SPEAKING = "speaking"
    ERROR = "error"
    KILLED = "killed"             # Kill switch active


@dataclass
class Intent:
    """A structured request from Body to Soul.
    
    The Body creates an Intent from user input and submits it
    through the protocol. The Soul processes it and returns a SoulResult.
    """
    text: str
    intent_type: str = "chat"          # chat | tool_use | file | voice | system_query
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    # metadata may include:
    #   file_path: str       — for file uploads
    #   voice_data: bytes    — for voice input
    #   source: str          — "text_input" | "voice" | "file_drop"


@dataclass
class ToolProposal:
    """A single tool invocation PROPOSED by the Soul.
    
    The Soul proposes. The operator decides. Tools execute.
    This is the core of the three-tier authority model.
    """
    tool_name: str
    params: dict[str, Any]
    risk: RiskLevel
    reason: str                     # Why the Soul wants to run this
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approval_required: bool = True   # HIGH-risk always True
    safety_verdict: SafetyVerdict = SafetyVerdict.APPROVED
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolCall:
    """A single tool invocation that has been APPROVED for execution."""
    tool_name: str
    params: dict[str, Any]
    risk: RiskLevel
    approval_required: bool
    safety_verdict: SafetyVerdict = SafetyVerdict.APPROVED
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    approved_by: str = "operator"   # who approved this


@dataclass
class ToolResult:
    """Outcome of executing a single tool."""
    call_id: str
    tool_name: str
    status: str                         # "success" | "error" | "blocked" | "approval_required"
    result: Any = None
    error: str | None = None
    severity: ErrorSeverity = ErrorSeverity.PERMANENT
    duration_ms: int = 0


@dataclass
class ApprovalWindow:
    """Tracks a pending approval request for HIGH-risk tools.
    
    The Soul proposes. The Body shows the dialog. The operator decides.
    If the operator doesn't decide within timeout, it expires.
    """
    proposal_id: str
    tool_name: str
    params: dict[str, Any]
    risk: RiskLevel
    reason: str                       # Why the Soul wants to run this
    created_at: float = field(default_factory=lambda: __import__('time').time())
    timeout_seconds: int = 300        # 5 minutes default
    status: ApprovalStatus = ApprovalStatus.PENDING


@dataclass
class SoulResult:
    """The Soul's response to an Intent.
    
    Contains the response text, any tool proposals (not executions!),
    and the safety verdict for the overall operation.
    
    The Body uses this to:
    - Show the response to the user
    - Handle tool proposals based on risk level
    - Update the HUD state
    """
    request_id: str
    response: str
    state: SoulState = SoulState.IDLE
    safety_verdict: SafetyVerdict = SafetyVerdict.APPROVED
    
    # Proposals — the Soul proposes, the operator decides
    tool_proposals: list[ToolProposal] = field(default_factory=list)
    
    # Results — only populated after execution
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    
    # Approval tracking
    needs_approval: bool = False       # True if HIGH-risk proposals exist
    approval_id: str | None = None     # ID for the approval dialog
    
    agent_used: str = ""
    duration_ms: int = 0
    error: str | None = None


@dataclass
class KillSwitchState:
    """State of the kill switch — the operator's ultimate override.
    
    When active, the Soul halts ALL execution immediately.
    No tool can run. No proposal can be approved.
    The Soul itself stops processing.
    """
    active: bool = False
    activated_at: float | None = None
    reason: str = ""
    activated_by: str = "operator"
