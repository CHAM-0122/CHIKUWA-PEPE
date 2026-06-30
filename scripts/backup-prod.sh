#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
KEEP_DAYS="${2:-7}"
cd "$APP_DIR"

if [ ! -f .env.production ]; then
  echo ".env.production がありません。"
  exit 1
fi

set -a
source .env.production
set +a

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$APP_DIR/backups/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

COMPOSE_FILES=(-f docker-compose.https.yml)
if [ -f docker-compose.logs.yml ]; then
  COMPOSE_FILES+=(-f docker-compose.logs.yml)
fi

COMPOSE=(docker compose --env-file .env.production "${COMPOSE_FILES[@]}")

echo "Backing up PostgreSQL..."
"${COMPOSE[@]}" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_DIR/database.sql"

echo "Backing up uploads..."
tar -czf "$BACKUP_DIR/uploads.tar.gz" uploads

cat > "$BACKUP_DIR/README.txt" <<INFO
Backup created: $TIMESTAMP
Database: $POSTGRES_DB
User: $POSTGRES_USER
App dir: $APP_DIR
INFO

find "$APP_DIR/backups" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
