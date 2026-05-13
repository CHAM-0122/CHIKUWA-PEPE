#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
HOURS_BACK="${2:-24}"
cd "$APP_DIR"

if [ ! -f .env.production ]; then
  echo ".env.production がありません。"
  exit 1
fi

AWS_REGION_VALUE=$(grep '^AWS_REGION=' .env.production | cut -d= -f2-)
LOG_GROUP=$(grep '^CLOUDWATCH_LOG_GROUP=' .env.production | cut -d= -f2-)
S3_BUCKET=$(grep '^S3_LOG_ARCHIVE_BUCKET=' .env.production | cut -d= -f2-)

if [ -z "$AWS_REGION_VALUE" ] || [ -z "$LOG_GROUP" ] || [ -z "$S3_BUCKET" ]; then
  echo "AWS_REGION, CLOUDWATCH_LOG_GROUP, S3_LOG_ARCHIVE_BUCKET を .env.production に設定してください。"
  exit 1
fi

NOW_EPOCH=$(date +%s)
FROM_EPOCH=$((NOW_EPOCH - HOURS_BACK * 3600))
FROM_MS=$((FROM_EPOCH * 1000))
TO_MS=$((NOW_EPOCH * 1000))
TASK_NAME="dog-growth-journal-export-$(date +%Y%m%d%H%M%S)"
PREFIX="cloudwatch-export/$(date +%Y/%m/%d)"

aws logs create-export-task   --task-name "$TASK_NAME"   --log-group-name "$LOG_GROUP"   --from "$FROM_MS"   --to "$TO_MS"   --destination "$S3_BUCKET"   --destination-prefix "$PREFIX"   --region "$AWS_REGION_VALUE"

echo "Started export task: $TASK_NAME"
