#!/usr/bin/env python3
"""MCP HTTP Bridge — wraps stdio MCP servers as HTTP endpoints.

Used by docker-compose (mcp-bridge service) to let Python tools call MCP
servers over HTTP instead of managing subprocesses directly.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)
_processes: dict[str, subprocess.Popen] = {}

REGISTRY_PATH = Path("/app/mcp-servers/mcp-registry.json")


def _start_server(name: str) -> subprocess.Popen:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    cfg = payload.get("mcp_servers", {}).get(name, {})
    cmd = cfg.get("install_command", "")
    if not cmd:
        raise ValueError(f"Unknown MCP server: {name}")
    proc = subprocess.Popen(
        cmd.split(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    init = json.dumps({
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "jarvis-bridge", "version": "1.0.0"},
        },
    }) + "\n"
    if proc.stdin is None:
        raise RuntimeError("No stdin")
    proc.stdin.write(init)
    proc.stdin.flush()
    if proc.stdout is None:
        raise RuntimeError("No stdout")
    proc.stdout.readline()  # consume initialize response
    return proc


def _mcp_request(proc: subprocess.Popen, method: str, params: dict[str, Any]) -> dict[str, Any]:
    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Process pipes not available")
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}) + "\n"
    proc.stdin.write(req)
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("MCP server closed connection")
    resp = json.loads(line)
    if "error" in resp:
        raise RuntimeError(f"MCP error: {resp['error']}")
    return resp.get("result", {})


@app.route("/tools/call", methods=["POST"])
@app.route("/call", methods=["POST"])
def call_tool() -> Any:
    data = request.get_json(force=True)
    server_name = data.get("server", "search-mcp")
    tool = data.get("tool", "search")
    arguments = data.get("arguments", {})

    try:
        if server_name not in _processes:
            _processes[server_name] = _start_server(server_name)
        result = _mcp_request(_processes[server_name], "tools/call", {"name": tool, "arguments": arguments})
        return jsonify({"jsonrpc": "2.0", "id": 1, "result": result})
    except Exception as exc:
        return jsonify({"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": str(exc)}}), 502


@app.route("/health")
def health() -> Any:
    return jsonify({"status": "ok", "servers": list(_processes.keys())})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    app.run(host="0.0.0.0", port=port)
