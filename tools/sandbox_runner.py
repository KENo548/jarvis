#!/usr/bin/env python3
"""Local isolated sandbox runner for JARVIS.

Runs Python snippets in isolated mode with a minimal environment and a temp
working directory. This is not a full container sandbox, but it is a safe,
free local execution harness for Phase 3 development.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


PYTHON = Path("c:/python314/python.exe")


@dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str


def run_python_snippet(code: str, timeout_seconds: int = 5) -> SandboxResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = {
            "SystemRoot": os.environ.get("SystemRoot", "C:\\Windows"),
            "WINDIR": os.environ.get("WINDIR", "C:\\Windows"),
            "TEMP": temp_dir,
            "TMP": temp_dir,
        }
        completed = subprocess.run(
            [str(PYTHON), "-I", "-S", "-c", code],
            cwd=temp_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return SandboxResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS local sandbox runner")
    parser.add_argument("code")
    parser.add_argument("--timeout-seconds", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_python_snippet(args.code, timeout_seconds=args.timeout_seconds)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=os.sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())