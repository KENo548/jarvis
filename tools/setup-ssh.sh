# =============================================================================
# JARVIS SSH Hardening Script (Linux)
# =============================================================================
# Generates Ed25519 SSH keypair and configures server for key-only auth.
# Run on the TARGET SERVER as root or with sudo.
#
# Run: sudo bash tools/setup-ssh.sh
# =============================================================================

set -euo pipefail

echo "=== JARVIS SSH Hardening ==="
echo ""

# --- Step 1: Generate Ed25519 keypair (if none exists) ---
KEY_PATH="$HOME/.ssh/id_ed25519_jarvis"
if [ -f "$KEY_PATH" ]; then
    echo "[1/4] SSH key already exists at $KEY_PATH"
else
    echo "[1/4] Generating Ed25519 SSH keypair..."
    ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "jarvis@$(hostname)"
    echo "  Key generated: $KEY_PATH"
    echo "  Public key: ${KEY_PATH}.pub"
fi

# --- Step 2: Add public key to authorized_keys ---
echo "[2/4] Adding public key to authorized_keys..."
AUTH_KEYS="$HOME/.ssh/authorized_keys"
touch "$AUTH_KEYS"
chmod 600 "$AUTH_KEYS"
if grep -qF "$(cat "${KEY_PATH}.pub")" "$AUTH_KEYS" 2>/dev/null; then
    echo "  Public key already in authorized_keys."
else
    cat "${KEY_PATH}.pub" >> "$AUTH_KEYS"
    echo "  Public key added to authorized_keys."
fi

# --- Step 3: Harden sshd_config ---
echo "[3/4] Hardening sshd_config..."
SSHD_CONFIG="/etc/ssh/sshd_config"
if [ -f "$SSHD_CONFIG" ]; then
    cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak.$(date +%s)"
    echo "  Backup created."

    # Apply hardening (idempotent)
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"
    sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' "$SSHD_CONFIG"
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' "$SSHD_CONFIG"
    sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' "$SSHD_CONFIG"
    sed -i 's/^#\?UsePAM.*/UsePAM no/' "$SSHD_CONFIG"

    echo "  sshd_config updated:"
    echo "    PasswordAuthentication no"
    echo "    PubkeyAuthentication yes"
    echo "    PermitRootLogin prohibit-password"
    echo "    ChallengeResponseAuthentication no"
else
    echo "  WARNING: $SSHD_CONFIG not found. Skipping sshd_config changes."
fi

# --- Step 4: Restart SSH ---
echo "[4/4] Restarting SSH service..."
if command -v systemctl &>/dev/null; then
    systemctl restart sshd
    echo "  sshd restarted."
elif command -v service &>/dev/null; then
    service ssh restart
    echo "  ssh restarted."
else
    echo "  WARNING: Could not restart sshd. Run manually: systemctl restart sshd"
fi

echo ""
echo "=== SSH Hardening Complete ==="
echo "  Key pair: $KEY_PATH"
echo "  Copy the private key to your local machine:"
echo "    scp $(hostname):$KEY_PATH ~/.ssh/id_ed25519_jarvis"
echo ""
echo "  WARNING: Test SSH login in a NEW terminal before closing this one!"
echo "  If locked out, use the backup: sudo cp ${SSHD_CONFIG}.bak.* $SSHD_CONFIG && sudo systemctl restart sshd"
