# =============================================================================
# JARVIS HTTPS Reverse Proxy — Nginx + Let's Encrypt
# =============================================================================
# Terminates TLS for all JARVIS services. Free certificates via Let's Encrypt.
#
# Setup:
#   1. Point your domain's DNS to this server
#   2. Set DOMAIN in secrets/nginx.env (e.g., jarvis.example.com)
#   3. Set EMAIL for Let's Encrypt notifications
#   4. Add nginx service to docker-compose.yml (see below)
#   5. Run: docker compose up -d nginx
#
# This is an ALTERNATIVE to running services on plain HTTP.
# Use this when exposing services beyond localhost.
# =============================================================================

# --- Nginx service block (add to docker-compose.yml) ---
# nginx:
#   image: nginx:alpine
#   container_name: jarvis-nginx
#   restart: unless-stopped
#   volumes:
#     - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
#     - ./nginx/certs:/etc/nginx/certs
#     - nginx-data:/var/cache/nginx
#   networks:
#     - jarvis-net
#   ports:
#     - "443:443"
#     - "80:80"
#   depends_on:
#     - grafana
#     - n8n
#     - searxng

# --- Nginx config ---
# worker_processes auto;
# events { worker_connections 1024; }
# http {
#   # Rate limiting
#   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
#
#   server {
#     listen 80;
#     server_name _;
#     # Redirect all HTTP to HTTPS
#     return 301 https://$host$request_uri;
#   }
#
#   server {
#     listen 443 ssl;
#     server_name jarvis.example.com;
#
#     ssl_certificate     /etc/nginx/certs/fullchain.pem;
#     ssl_certificate_key /etc/nginx/certs/privkey.pem;
#     ssl_protocols       TLSv1.2 TLSv1.3;
#     ssl_ciphers         HIGH:!aNULL:!MD5;
#
#     # Grafana
#     location /grafana/ {
#       proxy_pass http://grafana:3000/;
#       limit_req zone=api burst=20 nodelay;
#     }
#
#     # n8n
#     location /n8n/ {
#       proxy_pass http://n8n:5678/;
#       limit_req zone=api burst=10 nodelay;
#     }
#
#     # SearXNG
#     location /search/ {
#       proxy_pass http://searxng:8080/;
#       limit_req zone=api burst=10 nodelay;
#     }
#   }
# }

# --- Let's Encrypt certbot ---
# Use certbot with DNS challenge for automatic cert renewal:
#   docker run --rm -v ./nginx/certs:/etc/letsencrypt \
#     certbot/certbot certonly --standalone \
#     -d jarvis.example.com --email admin@example.com --agree-tos
#
# Auto-renewal cron (add to crontab):
#   0 3 * * * docker run --rm -v ./nginx/certs:/etc/letsencrypt certbot/certbot renew
