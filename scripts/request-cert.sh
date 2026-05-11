#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
DOMAIN="${2:-}"
EMAIL="${3:-}"

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "Usage: ./scripts/request-cert.sh <app_dir> <domain> <email>"
  echo "Example: ./scripts/request-cert.sh "$HOME/CHIKUWA-PEPE" chamcham.blog you@example.com"
  exit 1
fi

cd "$APP_DIR"
mkdir -p certbot/www

docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml down

sudo docker run --rm   -p 80:80   -v /etc/letsencrypt:/etc/letsencrypt   -v /var/lib/letsencrypt:/var/lib/letsencrypt   certbot/certbot certonly --standalone   -d "$DOMAIN"   --non-interactive   --agree-tos   -m "$EMAIL"

echo "Certificate issued for $DOMAIN"
