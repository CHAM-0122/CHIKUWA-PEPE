#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
cd "$APP_DIR"

if [ ! -f .env.production ]; then
  echo ".env.production がありません。"
  exit 1
fi

COMPOSE_FILES=(-f docker-compose.https.yml)
if [ -f docker-compose.logs.yml ]; then
  COMPOSE_FILES+=(-f docker-compose.logs.yml)
fi

COMPOSE=(docker compose --env-file .env.production "${COMPOSE_FILES[@]}")

echo "== Compose Status =="
"${COMPOSE[@]}" ps

echo
printf '== Healthz ==
'
if curl -kfsS --max-time 5 https://localhost/healthz; then
  printf '
'
else
  printf '
healthz check failed
'
fi

echo
echo "== Recent App Logs =="
"${COMPOSE[@]}" logs app --tail=30 || true

echo
echo "== Recent Nginx Logs =="
"${COMPOSE[@]}" logs nginx --tail=20 || true

echo
echo "== Disk Usage =="
df -h /
