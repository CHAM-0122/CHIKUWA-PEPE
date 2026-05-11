#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
cd "$APP_DIR"

if [ ! -f .env.production ]; then
  echo ".env.production がありません。.env.production.example を元に作成してください。"
  exit 1
fi

docker compose   --env-file .env.production   -f docker-compose.yml   -f docker-compose.prod.yml   up -d --build

docker compose   --env-file .env.production   -f docker-compose.yml   -f docker-compose.prod.yml   ps
