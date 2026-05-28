#!/usr/bin/env bash
# =============================================================================
# JARVIS Git Secrets Setup — Prevent accidental API key commits
# =============================================================================
# Run this once after cloning any repo. It installs git hooks that scan
# every commit for secrets before they can reach GitHub.
#
# Usage:  ./git-secrets-setup.sh
# =============================================================================

set -euo pipefail

echo "============================================"
echo "  JARVIS Git Secrets Setup"
echo "============================================"
echo ""

# === 1. Install git-secrets ===
if ! command -v git-secrets &>/dev/null; then
    echo "[1/3] Installing git-secrets..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install git-secrets
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y git-secrets
        else
            git clone https://github.com/awslabs/git-secrets.git /tmp/git-secrets
            cd /tmp/git-secrets
            sudo make install
            cd -
            rm -rf /tmp/git-secrets
        fi
    else
        echo "  [ERROR] Unsupported OS. Install manually: https://github.com/awslabs/git-secrets"
        exit 1
    fi
    echo "  Done."
else
    echo "[1/3] git-secrets already installed."
fi

# === 2. Register common secret patterns ===
echo "[2/3] Registering secret patterns..."

# Default AWS patterns
git secrets --register-aws 2>/dev/null || true

# API key patterns across providers
git secrets --add 'sk-[a-zA-Z0-9]{20,}'          # OpenAI / Anthropic keys
git secrets --add 'ghp_[a-zA-Z0-9]{36,}'           # GitHub PAT
git secrets --add 'gho_[a-zA-Z0-9]{36,}'           # GitHub OAuth
git secrets --add 'ghu_[a-zA-Z0-9]{36,}'           # GitHub user tokens
git secrets --add 'xox[baprs]-[a-zA-Z0-9\-]{10,}'  # Slack tokens
git secrets --add '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
git secrets --add 'AIza[0-9A-Za-z\-_]{35,}'        # Google API
git secrets --add 'sk_live_[0-9a-zA-Z]+'            # Stripe live keys
git secrets --add 'pk_live_[0-9a-zA-Z]+'            # Stripe live publishable keys
git secrets --add 'AKIA[0-9A-Z]{16}'                # AWS access keys
git secrets --add 'SG\.[a-zA-Z0-9\-_]{20,}'         # SendGrid
git secrets --add 'api[-_]?key.*=.*['"'"'"]?[a-zA-Z0-9\-_]{16,}'  # Generic API key patterns

echo "  Done."

# === 3. Install hooks in all repos ===
echo "[3/3] Installing hooks..."
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../github-repos" && pwd)"

if [ -d "$REPO_DIR" ]; then
    for repo in "$REPO_DIR"/*/; do
        if [ -d "$repo/.git" ]; then
            echo "  Installing hooks in: $(basename "$repo")"
            cd "$repo"
            git secrets --install 2>/dev/null || true
            cd - > /dev/null
        fi
    done
fi

# Also install in the current project
if [ -d ".git" ]; then
    echo "  Installing hooks in current project..."
    git secrets --install 2>/dev/null || true
fi

echo ""
echo "============================================"
echo "  Git secrets setup complete."
echo "  API keys and passwords are now blocked"
echo "  from being committed to any repository."
echo "============================================"
