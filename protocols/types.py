"""Data types for the SoulBodyProtocol contract."""

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
    """Risk classification for tool execution."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


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
    EXECUTING = "executing"
    SPEAKING = "speaking"
    ERROR = "error"


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
class ToolCall:
    """A single tool invocation decided by the Soul."""
    tool_name: str
    params: dict[str, Any]
    risk: RiskLevel
    approval_required: bool
    safety_verdict: SafetyVerdict = SafetyVerdict.APPROVED
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


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
class SoulResult:
    """The Soul's response to an Intent.
    
    Contains the response text, any tool calls made (or pending),
    and the safety verdict for the overall operation.
    """
    request_id: str
    response: str
    state: SoulState = SoulState.IDLE
    safety_verdict: SafetyVerdict = SafetyVerdict.APPROVED
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    needs_approval: bool = False
    approval_id: str | None = None
    agent_used: str = ""
    duration_ms: int = 0
    error: str | None = None
