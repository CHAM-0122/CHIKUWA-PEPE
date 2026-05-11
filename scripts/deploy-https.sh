#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
cd "$APP_DIR"

if [ ! -f .env.production ]; then
  echo ".env.production がありません。"
  exit 1
fi

if [ ! -f /etc/letsencrypt/live/chamcham.blog/fullchain.pem ]; then
  echo "Let's Encrypt 証明書が見つかりません。先に ./scripts/request-cert.sh を実行してください。"
  exit 1
fi

mkdir -p certbot/www

docker compose --env-file .env.production -f docker-compose.https.yml down

docker compose --env-file .env.production -f docker-compose.https.yml up -d --build

docker compose --env-file .env.production -f docker-compose.https.yml ps
