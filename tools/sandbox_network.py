#!/usr/bin/env python3
"""
JARVIS Docker Sandbox Network — Isolated Execution
====================================================
Creates and manages an isolated Docker network for sandbox execution.
No internet access by default. Containers run in network isolation.

Usage:
    python tools/sandbox_network.py create    # Create isolated sandbox network
    python tools/sandbox_network.py destroy   # Remove sandbox network
    python tools/sandbox_network.py status    # Show network status
    python tools/sandbox_network.py run <code> # Run code in isolated container
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SANDBOX_NETWORK = "jarvis-sandbox-net"
SANDBOX_CONTAINER = "jarvis-sandbox"


def run_docker(args: list[str], check=True) -> subprocess.CompletedResult:
    return subprocess.run(
        ["docker"] + args,
        capture_output=True, text=True, check=check
    )


def create_network():
    """Create an isolated Docker network with no internet."""
    # Check if exists
    result = run_docker(["network", "inspect", SANDBOX_NETWORK], check=False)
    if result.returncode == 0:
        print(f"Network {SANDBOX_NETWORK} already exists.")
        return

    # Create internal network (no internet)
    run_docker([
        "network", "create",
        "--internal",  # No internet access
        "--driver", "bridge",
        "--subnet", "172.30.0.0/16",
        SANDBOX_NETWORK
    ])
    print(f"Created isolated network: {SANDBOX_NETWORK}")
    print("  Internet access: DISABLED")
    print("  Subnet: 172.30.0.0/16")


def destroy_network():
    """Remove the sandbox network."""
    # Remove any containers on the network first
    result = run_docker(["ps", "-a", "--filter", f"network={SANDBOX_NETWORK}", "-q"], check=False)
    if result.stdout.strip():
        container_ids = result.stdout.strip().split("\n")
        for cid in container_ids:
            run_docker(["rm", "-f", cid], check=False)
            print(f"  Removed container: {cid[:12]}")

    run_docker(["network", "rm", SANDBOX_NETWORK], check=False)
    print(f"Removed network: {SANDBOX_NETWORK}")


def show_status():
    """Show sandbox network status."""
    result = run_docker(["network", "inspect", SANDBOX_NETWORK], check=False)
    if result.returncode != 0:
        print(f"Network {SANDBOX_NETWORK} does not exist.")
        print("Create it: python tools/sandbox_network.py create")
        return

    data = json.loads(result.stdout)
    info = data[0] if data else {}
    print(f"=== Sandbox Network: {SANDBOX_NETWORK} ===")
    print(f"  Driver: {info.get('Driver', 'unknown')}")
    print(f"  Internal (no internet): {info.get('Internal', 'unknown')}")

    containers = info.get("Containers", {})
    print(f"  Containers: {len(containers)}")
    for cid, cinfo in containers.items():
        print(f"    {cinfo.get('Name', cid[:12])}: {cinfo.get('IPv4Address', 'no IP')}")


def run_in_sandbox(code: str, timeout: int = 30):
    """Run Python code in an isolated Docker container."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        code_file = f.name

    try:
        result = run_docker([
            "run", "--rm",
            "--network", SANDBOX_NETWORK,
            "--read-only",
            "--tmpfs", "/tmp:size=10m",
            "-v", f"{code_file}:/code.py:ro",
            "python:3.14-slim",
            "python", "/code.py"
        ], check=False)

        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    finally:
        Path(code_file).unlink(missing_ok=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        create_network()
    elif command == "destroy":
        destroy_network()
    elif command == "status":
        show_status()
    elif command == "run":
        if len(sys.argv) < 3:
            print("Usage: sandbox_network.py run <python_code>")
            sys.exit(1)
        code = " ".join(sys.argv[2:])
        sys.exit(run_in_sandbox(code))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
