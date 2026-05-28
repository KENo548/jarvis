#!/usr/bin/env python3
"""
JARVIS Trivy Security Scanner — Container & Code Vulnerability Scanning
=======================================================================
Replaces Falco (incompatible with Windows Docker Desktop).
Scans container images, IaC configs, dependencies, and secrets.

Usage:
    python tools/trivy_scan.py image <image_name>     # Scan a Docker image
    python tools/trivy_scan.py fs <path>              # Scan filesystem
    python tools/trivy_scan.py config <path>          # Scan IaC configs
    python tools/trivy_scan.py all                    # Scan all JARVIS images
    python tools/trivy_scan.py report                 # Full security report
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TRIVY_CONTAINER = "jarvis-trivy"
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
REPORT_DIR = LOG_DIR / "trivy-reports"


def run_trivy(args: list[str], timeout: int = 300) -> dict:
    cmd = ["docker", "exec", TRIVY_CONTAINER, "trivy", "--format", "json"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Scan timed out"}


def scan_image(image: str) -> dict:
    print(f"Scanning image: {image}...")
    result = run_trivy(["image", "--severity", "HIGH,CRITICAL", image])
    if result["returncode"] == 0 and result["stdout"]:
        data = json.loads(result["stdout"])
        vulns = []
        for artifact in data.get("Results", []):
            for v in artifact.get("Vulnerabilities", []):
                vulns.append({
                    "id": v.get("VulnerabilityID"),
                    "severity": v.get("Severity"),
                    "pkg": v.get("PkgName"),
                    "installed": v.get("InstalledVersion"),
                    "fixed": v.get("FixedVersion"),
                    "title": v.get("Title", "")[:80],
                })
        return {"image": image, "vulnerabilities": vulns, "count": len(vulns)}
    return {"image": image, "error": result["stderr"], "vulnerabilities": [], "count": 0}


def scan_filesystem(path: str) -> dict:
    print(f"Scanning filesystem: {path}...")
    result = run_trivy(["fs", "--severity", "HIGH,CRITICAL", path])
    if result["returncode"] == 0 and result["stdout"]:
        data = json.loads(result["stdout"])
        findings = []
        for artifact in data.get("Results", []):
            for v in artifact.get("Vulnerabilities", []):
                findings.append({
                    "id": v.get("VulnerabilityID"),
                    "severity": v.get("Severity"),
                    "target": artifact.get("Target"),
                    "pkg": v.get("PkgName"),
                    "title": v.get("Title", "")[:80],
                })
        return {"path": path, "findings": findings, "count": len(findings)}
    return {"path": path, "error": result["stderr"], "findings": [], "count": 0}


def scan_config(path: str) -> dict:
    print(f"Scanning IaC config: {path}...")
    result = run_trivy(["config", "--severity", "HIGH,CRITICAL", path])
    if result["returncode"] == 0 and result["stdout"]:
        data = json.loads(result["stdout"])
        misconfigs = []
        for artifact in data.get("Results", []):
            for m in artifact.get("Misconfigurations", []):
                misconfigs.append({
                    "id": m.get("ID"),
                    "severity": m.get("Severity"),
                    "title": m.get("Title"),
                    "message": m.get("Message", "")[:120],
                    "target": artifact.get("Target"),
                })
        return {"path": path, "misconfigurations": misconfigs, "count": len(misconfigs)}
    return {"path": path, "error": result["stderr"], "misconfigurations": [], "count": 0}


JARVIS_IMAGES = [
    "chromadb/chroma:latest",
    "n8nio/n8n:latest",
    "grafana/grafana:11.6.0",
    "prom/prometheus:v3.2.1",
    "grafana/loki:3.4.2",
    "hashicorp/vault:1.19.0",
    "searxng/searxng:latest",
    "neo4j:5.26.0-community",
    "nginx:alpine",
    "redis:7-alpine",
]


def scan_all() -> list[dict]:
    results = []
    for img in JARVIS_IMAGES:
        r = scan_image(img)
        results.append(r)
        status = f"{r['count']} vulnerabilities" if r["count"] == 0 or "error" not in r else f"ERROR: {r['error'][:50]}"
        print(f"  {img}: {status}")
    return results


def full_report() -> dict:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_scans": scan_all(),
        "filesystem_scan": scan_filesystem("/jarvis"),
        "config_scan": scan_config("/jarvis/infrastructure"),
    }

    total_vulns = sum(s["count"] for s in report["image_scans"])
    total_misconfigs = report["config_scan"]["count"]
    total_fs = report["filesystem_scan"]["count"]

    report["summary"] = {
        "total_image_vulnerabilities": total_vulns,
        "total_misconfigurations": total_misconfigs,
        "total_filesystem_findings": total_fs,
        "images_scanned": len(JARVIS_IMAGES),
    }

    out_path = REPORT_DIR / f"trivy-report-{ts}.json"
    out_path.write_text(json.dumps(report, indent=2))

    print(f"\n{'='*60}")
    print(f"TRIVY SECURITY REPORT — {ts}")
    print(f"{'='*60}")
    print(f"  Images scanned:              {len(JARVIS_IMAGES)}")
    print(f"  Image vulnerabilities:       {total_vulns}")
    print(f"  IaC misconfigurations:       {total_misconfigs}")
    print(f"  Filesystem findings:         {total_fs}")
    print(f"  Report saved to:             {out_path}")
    print(f"{'='*60}")

    return report


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "image" and len(sys.argv) >= 3:
        r = scan_image(sys.argv[2])
        print(json.dumps(r, indent=2))
    elif cmd == "fs" and len(sys.argv) >= 3:
        r = scan_filesystem(sys.argv[2])
        print(json.dumps(r, indent=2))
    elif cmd == "config" and len(sys.argv) >= 3:
        r = scan_config(sys.argv[2])
        print(json.dumps(r, indent=2))
    elif cmd == "all":
        results = scan_all()
        print(json.dumps(results, indent=2))
    elif cmd == "report":
        full_report()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
