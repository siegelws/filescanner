#!/usr/bin/env bash
# One-shot deploy for a fresh Ubuntu 24.04 server (Contabo / Hetzner / DO).
#
# Usage (on the server, as root):
#   bash <(curl -fsSL https://raw.githubusercontent.com/siegelws/filescanner/main/infra/deploy.sh) <domain>
# or:
#   cd /opt/filescanner && bash infra/deploy.sh <domain>
#
# Requires the .env file to already exist in /opt/filescanner with API keys.

set -euo pipefail

DOMAIN="${1:-}"
REPO="https://github.com/siegelws/filescanner.git"
INSTALL_DIR="/opt/filescanner"

if [[ -z "$DOMAIN" ]]; then
  echo "Usage: $0 <domain.com>"
  exit 1
fi

log() { echo -e "\n\033[1;36m[deploy]\033[0m $*"; }

# -----------------------------------------------------------------------------
log "1/8 — system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y curl git ca-certificates ufw certbot

# -----------------------------------------------------------------------------
log "2/8 — Docker Engine + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# -----------------------------------------------------------------------------
log "3/8 — firewall (allow 22/80/443 only)"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
yes | ufw enable || true

# -----------------------------------------------------------------------------
log "4/8 — clone or update repo"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# -----------------------------------------------------------------------------
log "5/8 — .env check"
if [[ ! -f .env ]]; then
  echo "ERROR: $INSTALL_DIR/.env not found."
  echo "Copy .env.example -> .env and fill in keys before re-running this script."
  exit 1
fi

# Auto-fill PUBLIC_API_URL / PUBLIC_WS_URL if missing
grep -q "^PUBLIC_API_URL=" .env || echo "PUBLIC_API_URL=https://${DOMAIN}" >> .env
grep -q "^PUBLIC_WS_URL=" .env  || echo "PUBLIC_WS_URL=wss://${DOMAIN}"  >> .env

# -----------------------------------------------------------------------------
log "6/8 — TLS cert via Let's Encrypt"
mkdir -p infra/tls
if [[ ! -s "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
  # Need port 80 free
  docker compose down nginx 2>/dev/null || true
  certbot certonly --standalone --non-interactive --agree-tos \
    -m "admin@${DOMAIN}" -d "${DOMAIN}"
fi
cp -L "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" infra/tls/fullchain.pem
cp -L "/etc/letsencrypt/live/${DOMAIN}/privkey.pem"   infra/tls/privkey.pem

# -----------------------------------------------------------------------------
log "7/8 — build & start stack"
docker compose build
docker compose up -d
sleep 6
docker compose exec -T api alembic upgrade head

# -----------------------------------------------------------------------------
log "8/8 — TLS renewal cron"
cat >/etc/cron.daily/filescanner-renew <<EOF
#!/usr/bin/env bash
certbot renew --quiet && {
  cp -L /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${INSTALL_DIR}/infra/tls/fullchain.pem
  cp -L /etc/letsencrypt/live/${DOMAIN}/privkey.pem   ${INSTALL_DIR}/infra/tls/privkey.pem
  docker compose -f ${INSTALL_DIR}/docker-compose.yml restart nginx
}
EOF
chmod +x /etc/cron.daily/filescanner-renew

log "DONE — https://${DOMAIN} should be live in ~30s once ClamAV finishes its first signature pull."
docker compose ps
