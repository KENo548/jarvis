# =============================================================================
# JARVIS Fail2Ban Configuration
# =============================================================================
# Protects SSH and web interfaces from brute-force attacks.
# Install on the TARGET SERVER: sudo apt install fail2ban
# Copy these configs: sudo cp infrastructure/fail2ban/*.conf /etc/fail2ban/
#
# Run: sudo systemctl enable --now fail2ban
# =============================================================================

# --- jail.local (main config) ---
# [DEFAULT]
# bantime  = 3600
# findtime = 600
# maxretry = 3
# backend  = systemd
# action   = %(action_)s
#
# [sshd]
# enabled  = true
# port     = ssh
# filter   = sshd
# logpath  = /var/log/auth.log
# maxretry = 3
# bantime  = 3600
#
# [nginx-http-auth]
# enabled  = true
# port     = http,https
# filter   = nginx-http-auth
# logpath  = /var/log/nginx/error.log
# maxretry = 5
# bantime  = 1800
#
# [nginx-limit-req]
# enabled  = true
# port     = http,https
# filter   = nginx-limit-req
# logpath  = /var/log/nginx/error.log
# maxretry = 10
# findtime = 60
# bantime  = 600
