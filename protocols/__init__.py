"""protocols — SoulBodyProtocol contract for JARVIS.

Three-tier control model:
  Tier 1 — YOU (operator): Approve/reject HIGH-risk; kill switch overrides everything
  Tier 2 — Soul (JARVIS): Classifies intent, plans, proposes actions
  Tier 3 — Tools/Embodiment: Only runs what cleared both above tiers

The Soul proposes. You decide. Tools execute.
"""

from protocols.types import (
    Intent,
    SoulResult,
    ToolCall,
    ToolProposal,
    ToolResult,
    SafetyVerdict,
    RiskLevel,
    ApprovalStatus,
    ApprovalWindow,
    ErrorSeverity,
    SoulState,
    KillSwitchState,
)
from protocols.soul_body import SoulBodyProtocol
from protocols.jarvis_soul import JarvisSoul

__all__ = [
    "Intent",
    "SoulResult",
    "ToolCall",
    "ToolProposal",
    "ToolResult",
    "SafetyVerdict",
    "RiskLevel",
    "ApprovalStatus",
    "ApprovalWindow",
    "ErrorSeverity",
    "SoulState",
    "KillSwitchState",
    "SoulBodyProtocol",
    "JarvisSoul",
]
