#!/usr/bin/env python3
"""MCP stdio client for JARVIS — calls MCP server tools via JSON-RPC subprocess.

Use this to invoke MCP servers (search-mcp, browser-mcp, etc.) directly from
Python without requiring an HTTP bridge. Falls back gracefully if the MCP
package is not installed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


class MCPError(RuntimeError):
    pass


class MCPClient:
    _request_id: int = 0
    _process: subprocess.Popen | None = None

    def __init__(self, install_command: str, timeout_seconds: int = 30) -> None:
        parts = _split_command(install_command)
        executable = shutil.which(parts[0])
        if executable is None:
            raise MCPError(f"MCP executable not found: {parts[0]}")
        self._parts = [executable, *parts[1:]]
        self._timeout = timeout_seconds

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _ensure_running(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        self._process = subprocess.Popen(
            self._parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._request_id = 0
        self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "jarvis", "version": "1.0.0"},
            },
        )

    def close(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            # Close file handles to prevent ResourceWarning
            if self._process.stdin:
                try:
                    self._process.stdin.close()
                except Exception:
                    pass
            if self._process.stdout:
                try:
                    self._process.stdout.close()
                except Exception:
                    pass
            if self._process.stderr:
                try:
                    self._process.stderr.close()
                except Exception:
                    pass
            self._process = None

    def __enter__(self) -> MCPClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # JSON-RPC over stdio
    # ------------------------------------------------------------------

    def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise MCPError("MCP server not running")
        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params}
        self._process.stdin.write(json.dumps(request) + "\n")
        self._process.stdin.flush()
        line = self._process.stdout.readline()
        if not line:
            raise MCPError("MCP server closed connection unexpectedly")
        response = json.loads(line)
        if "error" in response:
            raise MCPError(f"MCP error ({response['error'].get('code', '?')}): {response['error'].get('message', 'unknown')}")
        return response.get("result", {})

    # ------------------------------------------------------------------
    # Tool operations
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        self._ensure_running()
        result = self._send_request("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any], timeout_seconds: int | None = None) -> dict[str, Any]:
        self._ensure_running()
        return self._send_request("tools/call", {"name": name, "arguments": arguments})


def _split_command(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in command.strip():
        if ch == '"':
            in_quote = not in_quote
        elif ch == " " and not in_quote:
            if buf:
                parts.append("".join(buf))
                buf.clear()
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts
