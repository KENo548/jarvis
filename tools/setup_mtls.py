#!/usr/bin/env python3
"""
JARVIS mTLS Certificate Generator — Zero-Trust Networking
==========================================================
Generates self-signed CA + per-service certificates for mutual TLS
between Docker Compose services.

Usage:
    python tools/setup_mtls.py init        # Generate CA + all service certs
    python tools/setup_mtls.py verify      # Verify cert chain
    python tools/setup_mtls.py list        # List generated certs

Certs are stored in infrastructure/certs/ and mounted into containers.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = PROJECT_ROOT / "infrastructure" / "certs"
CA_DIR = CERTS_DIR / "ca"

SERVICES = [
    "chroma", "redis", "n8n", "grafana", "loki", "prometheus",
    "vault", "searxng", "neo4j", "nginx", "mcp-bridge"
]


def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def generate_ca():
    """Generate a self-signed CA certificate."""
    CA_DIR.mkdir(parents=True, exist_ok=True)
    key_path = CA_DIR / "ca.key"
    cert_path = CA_DIR / "ca.crt"

    if key_path.exists() and cert_path.exists():
        print("CA already exists. Skipping.")
        return

    print("[1/3] Generating CA key...")
    run(["openssl", "genrsa", "-out", str(key_path), "4096"])

    print("[1/3] Generating CA certificate...")
    run([
        "openssl", "req", "-new", "-x509",
        "-key", str(key_path),
        "-out", str(cert_path),
        "-days", "3650",
        "-subj", "/C=US/ST=Local/L=JARVIS/O=JARVIS-CA/CN=JARVIS-Root-CA"
    ])
    print(f"  CA cert: {cert_path}")


def generate_service_cert(service: str):
    """Generate a service certificate signed by the CA."""
    svc_dir = CERTS_DIR / service
    svc_dir.mkdir(parents=True, exist_ok=True)
    key_path = svc_dir / f"{service}.key"
    csr_path = svc_dir / f"{service}.csr"
    cert_path = svc_dir / f"{service}.crt"
    ext_path = svc_dir / f"{service}.ext"

    if key_path.exists() and cert_path.exists():
        print(f"  {service}: certs exist. Skipping.")
        return

    # Generate key
    run(["openssl", "genrsa", "-out", str(key_path), "2048"])

    # Generate CSR
    run([
        "openssl", "req", "-new",
        "-key", str(key_path),
        "-out", str(csr_path),
        "-subj", f"/C=US/ST=Local/L=JARVIS/O=JARVIS/CN={service}"
    ])

    # Create extensions file for SAN
    ext_content = f"""authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=@alt_names

[alt_names]
DNS.1 = {service}
DNS.2 = jarvis-{service}
DNS.3 = localhost
IP.1 = 127.0.0.1
"""
    ext_path.write_text(ext_content)

    # Sign with CA
    run([
        "openssl", "x509", "-req",
        "-in", str(csr_path),
        "-CA", str(CA_DIR / "ca.crt"),
        "-CAkey", str(CA_DIR / "ca.key"),
        "-CAcreateserial",
        "-out", str(cert_path),
        "-days", "365",
        "-extfile", str(ext_path)
    ])

    # Cleanup CSR and ext
    csr_path.unlink(missing_ok=True)
    ext_path.unlink(missing_ok=True)

    print(f"  {service}: {cert_path}")


def list_certs():
    """List all generated certificates."""
    print("=== JARVIS mTLS Certificates ===\n")
    if not CERTS_DIR.exists():
        print("No certs directory found. Run: python tools/setup_mtls.py init")
        return

    ca_cert = CA_DIR / "ca.crt"
    if ca_cert.exists():
        result = run(["openssl", "x509", "-in", str(ca_cert), "-noout", "-subject", "-dates"], check=False)
        print(f"CA: {result.stdout.strip()}")
    print()

    for svc in SERVICES:
        svc_cert = CERTS_DIR / svc / f"{svc}.crt"
        if svc_cert.exists():
            result = run(["openssl", "x509", "-in", str(svc_cert), "-noout", "-subject", "-dates"], check=False)
            print(f"  {svc}: {result.stdout.strip()}")
        else:
            print(f"  {svc}: NOT GENERATED")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        print("=== JARVIS mTLS Certificate Generation ===\n")
        generate_ca()
        print(f"\n[2/3] Generating service certificates...")
        for svc in SERVICES:
            generate_service_cert(svc)
        print(f"\n[3/3] Certificates stored in: {CERTS_DIR}")
        print("\nTo enable mTLS in docker-compose, mount certs into each service.")

    elif command == "verify":
        print("=== Verifying Certificate Chain ===\n")
        for svc in SERVICES:
            cert = CERTS_DIR / svc / f"{svc}.crt"
            if cert.exists():
                result = run([
                    "openssl", "verify",
                    "-CAfile", str(CA_DIR / "ca.crt"),
                    str(cert)
                ], check=False)
                status = "OK" if "OK" in result.stdout else "FAILED"
                print(f"  {svc}: {status}")

    elif command == "list":
        list_certs()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
