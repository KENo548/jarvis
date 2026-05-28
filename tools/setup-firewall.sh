# =============================================================================
# JARVIS Firewall Configuration (Linux — UFW)
# =============================================================================
# Configures UFW with default-deny policy, allowing only SSH and VPN.
# Run on the TARGET SERVER as root or with sudo.
#
# Run: sudo bash tools/setup-firewall.sh
# =============================================================================

set -euo pipefail

SSH_PORT="${SSH_PORT:-22}"
VPN_PORT="${VPN_PORT:-41641}"

echo "=== JARVIS Firewall Configuration (UFW) ==="
echo ""

# --- Check UFW ---
if ! command -v ufw &>/dev/null; then
    echo "[1/5] UFW not found. Installing..."
    apt-get update -qq && apt-get install -y -qq ufw
else
    echo "[1/5] UFW found."
fi

# --- Reset to defaults ---
echo "[2/5] Resetting UFW to defaults..."
ufw --force reset

# --- Default policies: deny all inbound, allow all outbound ---
echo "[3/5] Setting default policies..."
ufw default deny incoming
ufw default allow outgoing

# --- Allow SSH ---
echo "[4/5] Allowing SSH on port $SSH_PORT..."
ufw allow "$SSH_PORT/tcp" comment "SSH"

# --- Allow Tailscale VPN ---
echo "[5/5] Allowing Tailscale VPN on port $VPN_PORT/UDP..."
ufw allow "$VPN_PORT/udp" comment "Tailscale VPN"

# --- Enable UFW ---
echo ""
echo "Enabling UFW..."
ufw --force enable

echo ""
echo "=== Firewall Configuration Complete ==="
ufw status verbose
echo ""
echo "IMPORTANT: Test SSH in a NEW terminal before closing this one!"
