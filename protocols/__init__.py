"""SoulBodyProtocol — the contract between JARVIS soul and Mark XXXIX body."""

from .types import (
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
from .soul_body import SoulBodyProtocol
from .jarvis_soul import JarvisSoul

__all__ = [
    "Intent",
    "SoulResult",
    "ToolCall",
    "ToolResult",
    "SafetyVerdict",
    "RiskLevel",
    "ApprovalStatus",
    "ErrorSeverity",
    "SoulState",
    "SoulBodyProtocol",
    "JarvisSoul",
]
