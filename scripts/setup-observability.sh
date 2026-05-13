#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
RETENTION_DAYS="${2:-30}"
cd "$APP_DIR"

if [ ! -f .env.production ]; then
  echo ".env.production がありません。"
  exit 1
fi

AWS_REGION_VALUE=$(grep '^AWS_REGION=' .env.production | cut -d= -f2-)
LOG_GROUP=$(grep '^CLOUDWATCH_LOG_GROUP=' .env.production | cut -d= -f2-)

if [ -z "$AWS_REGION_VALUE" ] || [ -z "$LOG_GROUP" ]; then
  echo "AWS_REGION または CLOUDWATCH_LOG_GROUP が .env.production にありません。"
  exit 1
fi

aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$AWS_REGION_VALUE" 2>/dev/null || true
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days "$RETENTION_DAYS" --region "$AWS_REGION_VALUE"

echo "CloudWatch Logs group ready: $LOG_GROUP"
