# =============================================================================
# JARVIS Tailscale VPN Setup (Linux)
# =============================================================================
# Installs Tailscale and joins your private mesh network.
# Free tier: up to 100 devices, no credit card required.
#
# Run: sudo bash tools/setup-tailscale.sh
# =============================================================================

set -euo pipefail

echo "=== JARVIS Tailscale VPN Setup ==="
echo ""
echo "Tailscale free tier: 100 devices, encrypted mesh, no credit card."
echo ""

# --- Install Tailscale ---
if command -v tailscale &>/dev/null; then
    echo "[1/3] Tailscale already installed."
else
    echo "[1/3] Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "  Tailscale installed."
fi

# --- Start Tailscale ---
echo "[2/3] Starting Tailscale..."
systemctl enable --now tailscaled
sleep 2

# --- Authenticate ---
echo "[3/3] Connecting to Tailscale network..."
echo "  This will open a browser for authentication."
echo "  If running headless, use: tailscale up --authkey=YOUR_KEY"
tailscale up

echo ""
echo "=== Tailscale Setup Complete ==="
echo ""
tailscale status
echo ""
echo "Your Tailscale IP:"
tailscale ip -4
echo ""
echo "Other machines on your network can now reach this server"
echo "via its Tailscale IP without exposing any ports."
