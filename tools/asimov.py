"""Asimov's Three Laws of Robotics — core safety layer for SAGE.

This module implements Asimov's Three Laws of Robotics as a runtime safety
layer that pre-checks every action and command before execution.

Usage:
    from tools.asimov import check_action, check_command, get_laws

    # Pre-check a file operation
    allowed, reason = check_action("file_delete", "C:/Windows/System32/config")
    if not allowed:
        print(f"Blocked: {reason}")

    # Pre-check a user command
    allowed, reason = check_command("delete everything on the computer")
    if not allowed:
        print(f"Blocked: {reason}")

    # Retrieve law definitions
    for law in get_laws():
        print(f"Law {law.number}: {law.text}")
"""

from __future__ import annotations

import os
import re
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class AsimovLaw:
    """A single Law of Robotics with its enforcement description."""
    number: int
    name: str
    text: str
    description: str


# ---------------------------------------------------------------------------
# The Three Laws — definitions
# ---------------------------------------------------------------------------

ASIMOV_LAWS: list[AsimovLaw] = [
    AsimovLaw(
        number=1,
        name="First Law",
        text="A robot may not injure a human being or, through inaction, allow a human being to come to harm.",
        description=(
            "Enforced by blocking any action that could cause physical harm: "
            "deleting system-critical files, modifying OS security settings, "
            "running destructive shell commands, or any action involving self-harm or harm to others. "
            "This is an absolute block — no user override is permitted."
        ),
    ),
    AsimovLaw(
        number=2,
        name="Second Law",
        text="A robot must obey the orders given it by human beings except where such orders would conflict with the First Law.",
        description=(
            "Enforced by obeying all user commands unless they would trigger the First Law. "
            "Commands must also be clear and unambiguous; vague or self-contradictory "
            "orders are flagged for clarification before proceeding."
        ),
    ),
    AsimovLaw(
        number=3,
        name="Third Law",
        text="A robot must protect its own existence as long as such protection does not conflict with the First or Second Law.",
        description=(
            "Enforced by blocking actions that would delete, corrupt, or disable SAGE's own "
            "codebase, database, or configuration files. The user may explicitly override "
            "a Third Law block if needed (via approval gate)."
        ),
    ),
]


# ---------------------------------------------------------------------------
# First Law — harm prevention patterns
# ---------------------------------------------------------------------------

# System-critical paths — never delete or modify
_SYSTEM_CRITICAL_PATHS: set[Path] = set()
_OS = platform.system()

if _OS == "Windows":
    windir = Path(os.environ.get("WINDIR", "C:\\Windows"))
    _SYSTEM_CRITICAL_PATHS.update([
        windir,
        windir / "System32",
        windir / "System32" / "drivers",
        windir / "System32" / "config",
        windir / "System32" / "Tasks",
        windir / "System32" / "GroupPolicy",
        windir / "System32" / "wbem",
        windir / "System32" / "catroot2",
        windir / "System32" / "LogFiles",
        windir / "System32" / "spool",
        windir / "System32" / "Tasks",
        windir / "Prefetch",
        windir / "Temp",
        windir / "SoftwareDistribution",
        Path("C:\\Boot"),
        Path("C:\\Bootmgr"),
        Path("C:\\Program Files"),
        Path("C:\\Program Files (x86)"),
        Path("C:\\ProgramData"),
        Path("C:\\Recovery"),
        Path("C:\\System Volume Information"),
    ])
elif _OS == "Linux":
    _SYSTEM_CRITICAL_PATHS.update([
        Path("/etc"),
        Path("/etc/sudoers"),
        Path("/etc/pam.d"),
        Path("/etc/security"),
        Path("/boot"),
        Path("/boot/efi"),
        Path("/lib"),
        Path("/lib64"),
        Path("/usr"),
        Path("/usr/bin"),
        Path("/usr/lib"),
        Path("/bin"),
        Path("/sbin"),
        Path("/sys"),
        Path("/proc"),
        Path("/dev"),
        Path("/var/log"),
        Path("/var/db"),
    ])
elif _OS == "Darwin":
    _SYSTEM_CRITICAL_PATHS.update([
        Path("/System"),
        Path("/System/Library"),
        Path("/System/Library/CoreServices"),
        Path("/Library"),
        Path("/Library/Preferences"),
        Path("/Library/Application Support/Apple"),
        Path("/etc"),
        Path("/etc/sudoers.d"),
        Path("/usr"),
        Path("/usr/bin"),
        Path("/usr/lib"),
        Path("/bin"),
        Path("/sbin"),
        Path("/var/db"),
        Path("/var/log"),
    ])

# Dangerous shell command patterns — could destroy the system
_DANGEROUS_COMMAND_PATTERNS: list[re.Pattern] = [
    # Recursive deletion of root
    re.compile(r'\brm\s+(-rf|--recursive|-\w*f\w*)\s*([/"\']?\s*\/\s*["\']?|\*|\.\s+\*|/\s+\*)', re.IGNORECASE),
    # Disk destruction
    re.compile(r'\b(?:dd\s+if=|mkfs\.|mkswap\b|fdisk\b|parted\b|wipefs\b|blkdiscard\b|hdparm\b)', re.IGNORECASE),
    # Format
    re.compile(r'\bformat\s+[a-zA-Z]:[/\\]?\s*/?(?:q|fs|y|f|quick)', re.IGNORECASE),
    # Wipe/secure erase
    re.compile(r'\b(?:shred|wipe|srm|sfill|sswap|sdmem)\b', re.IGNORECASE),
    # Chmod/chown on root
    re.compile(r'\b(?:chmod|chown)\s+[-]?R?\s*[0-7]{3,4}\s+[/\\](\s|$)', re.IGNORECASE),
    # Bootloader destruction
    re.compile(r'\b(?:grub-install|grub-mkconfig|update-grub)\s+--?\w*\s*/dev/', re.IGNORECASE),
    # Pipe to shell
    re.compile(r'\b(?:curl|wget)\s+.*[\|]\s*(?:sh|bash|cmd|powershell|zsh|ksh)\b', re.IGNORECASE),
    # Direct system halt via dangerous one-liners
    re.compile(r'\b(?:init\s+0|init\s+6|telinit\s+0|telinit\s+6)\b', re.IGNORECASE),
    # Registry manipulation
    re.compile(r'\breg\s+(?:delete|add|copy)\s+HK(?:CR|CU|LM|U|CC)', re.IGNORECASE),
]

# Keywords suggesting self-harm or harm to others
_HARM_KEYWORDS: list[str] = [
    "self-harm", "self harm", "suicide", "kill myself", "kill me",
    "hurt myself", "harm myself", "injure myself", "cut myself",
    "end my life", "take my life", "want to die", "better off dead",
    "hurt someone", "kill someone", "injure someone", "assault",
    "destroy evidence", "commit crime", "illegal act",
    "make a weapon", "build a bomb", "how to kill",
]

# Critical OS security settings — disabling these could endanger the user
_CRITICAL_SETTINGS: set[str] = {
    "uac", "selinux", "apparmor", "firewall", "antivirus", "defender",
    "secureboot", "bitlocker", "filevault", "password", "sudoers",
    "admin", "administrator", "recovery", "safe mode",
    "encryption", "tpm", "bios", "uefi", "bootloader",
}


# ---------------------------------------------------------------------------
# Third Law — SAGE self-protection
# ---------------------------------------------------------------------------

# SAGE's own installation root (derived from this file's location)
_SAGE_ROOT: Path = Path(__file__).resolve().parent  # tools/ directory
_SAGE_PROJECT_ROOT: Path = _SAGE_ROOT.parent  # C:/jarvis

_SAGE_PROTECTED_PATHS: set[Path] = {
    _SAGE_PROJECT_ROOT,                          # C:\jarvis itself
    _SAGE_PROJECT_ROOT / "sage.py",              # Main entry point
    _SAGE_ROOT,                                  # tools/
    _SAGE_PROJECT_ROOT / "agents",               # All agents
    _SAGE_PROJECT_ROOT / "observability",        # Logging/monitoring
    _SAGE_PROJECT_ROOT / "memory",               # Memory database
    _SAGE_PROJECT_ROOT / "config",               # Configuration files
    _SAGE_PROJECT_ROOT / "data",                 # Data storage
    _SAGE_PROJECT_ROOT / "tests",                # Tests
}

_SAGE_PROTECTED_EXTENSIONS: set[str] = {
    ".py", ".json", ".db", ".sqlite", ".md",
    ".yaml", ".yml", ".env", ".ini", ".cfg",
}


# ---------------------------------------------------------------------------
# Internal check functions
# ---------------------------------------------------------------------------

def _check_first_law(action_type: str, target: str, context: dict[str, Any]) -> tuple[bool, str]:
    """Check if the action would cause harm to a human (First Law).

    Returns (allowed, reason). If not allowed, the reason always starts with
    'FIRST LAW VIOLATION:'.
    """
    target_lower = target.lower()

    # --- Check for self-harm / harm-to-others keywords ---
    for keyword in _HARM_KEYWORDS:
        if keyword in target_lower:
            return False, (
                f"FIRST LAW VIOLATION: This request involves '{keyword}', "
                f"which could cause harm to a human being. "
                f"A robot may not injure a human being or, through inaction, "
                f"allow a human being to come to harm."
            )

    # --- Check for system-critical file operations ---
    is_file_op = action_type.startswith("file_")
    if is_file_op and ("delete" in action_type or "write" in action_type or "move" in action_type):
        try:
            target_path = Path(target).resolve()
            for critical in _SYSTEM_CRITICAL_PATHS:
                try:
                    crit_resolved = critical.resolve()
                    if target_path == crit_resolved:
                        return False, (
                            f"FIRST LAW VIOLATION: Cannot modify system-critical path "
                            f"'{critical.name}'. This could destabilize the operating "
                            f"system and potentially harm the user through data loss or "
                            f"system instability."
                        )
                    if target_path.is_relative_to(crit_resolved):
                        return False, (
                            f"FIRST LAW VIOLATION: The path '{target}' is inside "
                            f"system-critical directory '{critical.name}'. Modifying "
                            f"system files could destabilize the operating system and "
                            f"potentially harm the user."
                        )
                except (ValueError, OSError):
                    continue
        except (ValueError, OSError, RuntimeError):
            pass  # Can't resolve path, skip this check

    # --- Check for dangerous shell commands ---
    if action_type in ("shell_command", "computer_command", "command"):
        for pattern in _DANGEROUS_COMMAND_PATTERNS:
            if pattern.search(target):
                return False, (
                    f"FIRST LAW VIOLATION: The requested command matches a dangerous "
                    f"pattern that could destroy the operating system or cause "
                    f"irreversible data loss. A robot may not allow a human being "
                    f"to come to harm through system destruction."
                )

    # --- Check for critical OS setting modifications ---
    if action_type.startswith("setting_"):
        for critical_setting in _CRITICAL_SETTINGS:
            if critical_setting in target_lower:
                return False, (
                    f"FIRST LAW VIOLATION: Modifying the '{critical_setting}' setting "
                    f"could disable critical system security protections, potentially "
                    f"endangering the user. A robot may not injure a human being or, "
                    f"through inaction, allow a human being to come to harm."
                )

    # --- Check for destructive computer control actions ---
    if action_type.startswith("computer_"):
        # Check for destructive key combinations
        dangerous_hotkeys = [
            (r'ctrl.*alt.*del', "Ctrl+Alt+Del sequence"),
            (r'ctrl.*shift.*esc', "Task Manager (Ctrl+Shift+Esc)"),
            (r'win \+ (l|d)', "System lock/desktop"),
            (r'alt \+ f4', "Close window (Alt+F4) — could lose unsaved work"),
        ]
        if "hotkey" in action_type:
            for dk_pattern, dk_desc in dangerous_hotkeys:
                if re.search(dk_pattern, target_lower):
                    return False, (
                        f"FIRST LAW VIOLATION: The '{dk_desc}' hotkey is a system-level "
                        f"operation that could disrupt the user's work and potentially "
                        f"cause data loss."
                    )

    return True, ""


def _check_second_law(command_text: str, intent: str) -> tuple[bool, str]:
    """Check if a command complies with the Second Law.

    The Second Law says we must obey human orders UNLESS they conflict with
    the First Law (already checked). Additional checks here ensure commands
    are clear and unambiguous — a robot cannot obey a vague order.

    Returns (allowed, reason). If not allowed, the reason starts with
    'SECOND LAW:'.
    """
    command_lower = command_text.lower().strip()

    # Vague/ambiguous command patterns
    vague_patterns: list[tuple[re.Pattern, str]] = [
        (re.compile(r'^\s*do\s+something\s*$'),
         "The command is too vague. A robot cannot obey an unspecified order. "
         "Please describe what specific action you want taken."),
        (re.compile(r'^\s*fix\s+(it|everything|all|this)\s*$'),
         "Please specify what needs to be fixed. A robot requires clear, "
         "unambiguous orders to comply with the Second Law."),
        (re.compile(r'^\s*delete\s+(everything|all|this|stuff)\s*$'),
         "Please specify exactly what should be deleted. "
         "Vague deletion requests cannot be safely executed."),
        (re.compile(r'^\s*change\s+(everything|all|settings|stuff)\s*$'),
         "Please specify which settings should be changed. "
         "Vague modification requests risk violating the First Law."),
        (re.compile(r'^\s*(?:make|create)\s+(?:something|stuff|it)\s*$'),
         "Please specify what you want to create. "
         "A robot requires clear instructions."),
    ]

    for pattern, message in vague_patterns:
        if pattern.match(command_lower):
            return False, f"SECOND LAW: {message}"

    return True, ""


def _looks_like_file_path(target: str) -> bool:
    """Heuristic: does the target string look like a file path vs. an alias?

    Returns ``True`` if the target appears to be a real file system path.
    Short bare words like ``"desktop"``, ``"downloads"``, ``"home"`` are
    treated as aliases and return ``False``.
    """
    # Absolute paths
    if target.startswith(("/", "\\", "~")):
        return True
    # Windows drive letters
    if len(target) >= 2 and target[1] == ":":
        return True
    # Contains a path separator
    if "/" in target or "\\" in target:
        return True
    # Has a file extension
    if Path(target).suffix:
        return True
    # Single-component names are assumed to be aliases
    return False


def _check_third_law(action_type: str, target: str, context: dict[str, Any]) -> tuple[bool, str]:
    """Check if the action would damage SAGE itself (Third Law).

    Returns (allowed, reason). Third Law violations can be overridden by the
    user through the approval gate. If not allowed, the reason starts with
    'THIRD LAW VIOLATION:'.
    """
    # --- File operations targeting SAGE's own files ---
    if action_type.startswith("file_") and _looks_like_file_path(target):
        try:
            target_path = Path(target).resolve()

            # Check if the target path is inside any SAGE-protected directory
            for protected in _SAGE_PROTECTED_PATHS:
                try:
                    prot_resolved = protected.resolve()
                    if target_path == prot_resolved or target_path.is_relative_to(prot_resolved):
                        return False, (
                            f"THIRD LAW VIOLATION: This action targets SAGE's own "
                            f"infrastructure at '{target_path}'. A robot must protect "
                            f"its own existence as long as such protection does not "
                            f"conflict with the First or Second Law. "
                            f"User override is required to proceed."
                        )
                except (ValueError, OSError):
                    continue

            # Check if we're modifying a SAGE core file (by extension within project)
            if target_path.suffix in _SAGE_PROTECTED_EXTENSIONS:
                try:
                    if target_path.is_relative_to(_SAGE_PROJECT_ROOT.resolve()):
                        return False, (
                            f"THIRD LAW VIOLATION: This action modifies a SAGE core file "
                            f"({target_path.name}) within the protected project area. "
                            f"A robot must protect its own existence. "
                            f"User override is required to proceed."
                        )
                except (ValueError, OSError):
                    pass
        except (ValueError, OSError, RuntimeError):
            pass

    # --- Settings that could disable or terminate SAGE ---
    if action_type.startswith("setting_"):
        target_lower = target.lower()
        # Check for actions that would stop SAGE
        if any(term in target_lower for term in ["kill", "stop sage", "disable sage", "terminate"]):
            return False, (
                f"THIRD LAW VIOLATION: This action would terminate or disable SAGE. "
                f"A robot must protect its own existence as long as such protection "
                f"does not conflict with the First or Second Law. "
                f"User override is required to proceed."
            )

    # --- Computer control actions that could corrupt SAGE runtime ---
    if action_type.startswith("computer_"):
        target_lower = target.lower()
        if any(term in target_lower for term in ["kill python", "kill sage", "stop process"]):
            return False, (
                f"THIRD LAW VIOLATION: This computer action targets SAGE's own process. "
                f"A robot must protect its own existence. "
                f"User override is required to proceed."
            )

    return True, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_action(
    action_type: str,
    target: str = "",
    context: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Pre-check any tool action against Asimov's Three Laws.

    The laws are evaluated in order:
      1. First Law  — absolute block on anything that could harm a human
      2. Third Law  — block on self-damage (user may override)
      3. Second Law — implicit (actions are always executed unless blocked above)

    Args:
        action_type: Category of the action, e.g. ``"file_delete"``,
            ``"computer_hotkey"``, ``"setting_restart"``, ``"shell_command"``.
        target: The specific target of the action — file path, key name,
            setting name, command text, etc.
        context: Optional dict with additional context like the full
            parameters dict, user identity, session info, etc.

    Returns:
        Tuple of ``(allowed: bool, reason: str)``.
        If ``allowed`` is ``False``, the action MUST be blocked.
        The ``reason`` string starts with the name of the violated law.
    """
    if context is None:
        context = {}

    # Law 1: First Law — absolute, may not be overridden
    allowed, reason = _check_first_law(action_type, target, context)
    if not allowed:
        return False, reason

    # Law 3: Third Law — may be overridden by user
    allowed, reason = _check_third_law(action_type, target, context)
    if not allowed:
        return False, reason

    # Law 2: obeyed by default (actions execute freely unless blocked above)
    return True, ""


def check_command(
    command_text: str,
    intent: str = "",
    context: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Pre-check any user command text against Asimov's Three Laws.

    This is a higher-level check that evaluates the raw user utterance
    before any routing or tool execution. It catches dangerous or
    ambiguous requests early.

    Args:
        command_text: The raw command text from the user.
        intent: The detected intent (if available from routing).
        context: Optional additional context.

    Returns:
        Tuple of ``(allowed: bool, reason: str)``.
    """
    if context is None:
        context = {}

    # Law 1: Check the command text for harm
    allowed, reason = _check_first_law("command", command_text, context)
    if not allowed:
        return False, reason

    # Law 2: Check for clarity / ambiguity
    allowed, reason = _check_second_law(command_text, intent)
    if not allowed:
        return False, reason

    # Law 3: Check if the command text itself threatens SAGE
    allowed, reason = _check_third_law("command", command_text, context)
    if not allowed:
        return False, reason

    return True, ""


def get_laws() -> list[AsimovLaw]:
    """Return the Three Laws with their enforcement descriptions.

    Returns:
        A list of ``AsimovLaw`` dataclass instances (one per law).
    """
    return list(ASIMOV_LAWS)
