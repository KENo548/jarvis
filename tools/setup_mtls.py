#!/usr/bin/env python3
"""
JARVIS mTLS Certificate Generator — Zero-Trust Networking
=========================================================
Generates self-signed CA + per-service certificates for mutual TLS
between Docker Compose services. Uses Python cryptography library
(no openssl CLI required — works on Windows, Linux, macOS).

Usage:
    python tools/setup_mtls.py init        # Generate CA + all service certs
    python tools/setup_mtls.py verify      # Verify cert chain
    python tools/setup_mtls.py list        # List generated certs

Certs are stored in infrastructure/certs/ and mounted into containers.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print("ERROR: pip install cryptography")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = PROJECT_ROOT / "infrastructure" / "certs"
CA_DIR = CERTS_DIR / "ca"

SERVICES = [
    "chroma", "redis", "n8n", "grafana", "loki", "prometheus",
    "vault", "searxng", "neo4j", "nginx", "mcp-bridge",
]


def generate_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def generate_ca():
    CA_DIR.mkdir(parents=True, exist_ok=True)
    key_path = CA_DIR / "ca.key"
    cert_path = CA_DIR / "ca.crt"

    if key_path.exists() and cert_path.exists():
        print("CA already exists. Skipping.")
        return

    print("[1/3] Generating CA key...")
    key = generate_key()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.write_bytes(key_pem)

    print("[1/3] Generating CA certificate...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JARVIS"),
        x509.NameAttribute(NameOID.COMMON_NAME, "JARVIS Root CA"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    print(f"  CA cert: {cert_path}")


def generate_service_cert(service: str):
    svc_dir = CERTS_DIR / service
    svc_dir.mkdir(parents=True, exist_ok=True)
    key_path = svc_dir / f"{service}.key"
    cert_path = svc_dir / f"{service}.crt"

    if key_path.exists() and cert_path.exists():
        return

    ca_key_path = CA_DIR / "ca.key"
    ca_cert_path = CA_DIR / "ca.crt"
    ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
    ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())

    key = generate_key()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_path.write_bytes(key_pem)

    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JARVIS"),
        x509.NameAttribute(NameOID.COMMON_NAME, f"jarvis-{service}"),
    ])

    san_names = [x509.DNSName(f"jarvis-{service}"), x509.DNSName("localhost")]
    if service == "nginx":
        san_names.append(x509.DNSName("*"))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def init():
    print("=== JARVIS mTLS Certificate Generation ===\n")
    generate_ca()
    print(f"\n[2/3] Generating service certificates...")
    for svc in SERVICES:
        generate_service_cert(svc)
        print(f"  {svc}: {CERTS_DIR / svc / f'{svc}.crt'}")
    print(f"\n[3/3] Done. {len(SERVICES)} service certs generated.")
    print(f"  Certs directory: {CERTS_DIR}")


def verify():
    print("=== Verifying Certificate Chain ===\n")
    ca_cert_path = CA_DIR / "ca.crt"
    if not ca_cert_path.exists():
        print("ERROR: CA cert not found. Run 'init' first.")
        return
    ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
    print(f"CA: {ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}")
    print(f"  Valid: {ca_cert.not_valid_before_utc} to {ca_cert.not_valid_after_utc}")

    for svc in SERVICES:
        cert_path = CERTS_DIR / svc / f"{svc}.crt"
        if cert_path.exists():
            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            print(f"  {svc}: OK (CN={cn}, expires={cert.not_valid_after_utc})")
        else:
            print(f"  {svc}: MISSING")


def list_certs():
    print("=== Generated Certificates ===\n")
    for svc in SERVICES:
        cert_path = CERTS_DIR / svc / f"{svc}.crt"
        if cert_path.exists():
            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            print(f"  {svc}/  CN={cn}  expires={cert.not_valid_after_utc}")
        else:
            print(f"  {svc}/  NOT GENERATED")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "init":
        init()
    elif cmd == "verify":
        verify()
    elif cmd == "list":
        list_certs()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
