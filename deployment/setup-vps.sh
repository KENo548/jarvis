#!/bin/bash
# SAGE VPS Setup Script
# Run on Hetzner CX22 (Debian 12) to set up the VPS environment.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/your-repo/sage-vps-setup.sh | bash
#   Or: scp sage-vps-setup.sh root@<vps-ip>:~ && ssh root@<vps-ip> bash sage-vps-setup.sh

set -euo pipefail

echo "=== SAGE VPS Setup ==="
echo ""

# 1. System updates
echo "[1/7] System updates..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. Install Docker
echo "[2/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    usermod -aG docker $USER
fi
echo "  Docker: $(docker --version)"

# 3. Install Docker Compose
echo "[3/7] Installing Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi
echo "  Compose: $(docker compose version)"

# 4. Install Tailscale
echo "[4/7] Installing Tailscale..."
if ! command -v tailscale &> /dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
    systemctl enable tailscaled
    systemctl start tailscaled
fi
echo "  Tailscale: $(tailscale version | head -1)"

# 5. Pull Docker images
echo "[5/7] Pulling Docker images..."
docker pull ollama/ollama:latest
docker pull chromadb/chroma:latest
docker pull redis:7-alpine
docker pull grafana/loki:3.4.2
docker pull grafana/grafana:11.6.0
docker pull searxng/searxng:latest

# 6. Create directories
echo "[6/7] Creating directories..."
mkdir -p /opt/sage/data
mkdir -p /opt/sage/logs

# 7. Tailscale auth
echo "[7/7] Tailscale setup..."
echo ""
echo "Run the following command to authenticate Tailscale:"
echo "  sudo tailscale up --ssh"
echo ""
echo "After authentication, your VPS will be reachable at:"
echo "  $(tailscale ip -4 2>/dev/null || echo '<tailscale-ip>')"
echo ""

# Start services
echo "Starting SAGE services..."
cd /opt/sage
if [ -f docker-compose.vps.yml ]; then
    docker compose -f docker-compose.vps.yml up -d
    echo ""
    echo "=== SAGE VPS Ready ==="
    echo "  Grafana:    http://localhost:3000"
    echo "  SearXNG:    http://localhost:8888"
    echo "  Ollama:     http://localhost:11434"
    echo "  Chroma:     http://localhost:8000"
    echo "  Loki:       http://localhost:3100"
    echo ""
    echo "From your local machine (via Tailscale):"
    echo "  ssh root@<vps-tailscale-ip>"
    echo "  docker compose -f docker-compose.vps.yml logs -f"
else
    echo "Copy docker-compose.vps.yml to /opt/sage/ first."
fi
