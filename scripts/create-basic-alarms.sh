#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
INSTANCE_ID="${2:-}"
SNS_TOPIC_ARN="${3:-}"
cd "$APP_DIR"

if [ -z "$INSTANCE_ID" ] || [ -z "$SNS_TOPIC_ARN" ]; then
  echo "Usage: ./scripts/create-basic-alarms.sh <app_dir> <instance_id> <sns_topic_arn>"
  exit 1
fi

if [ ! -f .env.production ]; then
  echo ".env.production がありません。"
  exit 1
fi

AWS_REGION_VALUE=$(grep '^AWS_REGION=' .env.production | cut -d= -f2-)
LOG_GROUP=$(grep '^CLOUDWATCH_LOG_GROUP=' .env.production | cut -d= -f2-)

aws cloudwatch put-metric-alarm   --alarm-name "dog-growth-journal-${INSTANCE_ID}-cpu-high"   --alarm-description "EC2 CPU utilization is high"   --metric-name CPUUtilization   --namespace AWS/EC2   --statistic Average   --period 300   --threshold 80   --comparison-operator GreaterThanThreshold   --evaluation-periods 2   --dimensions Name=InstanceId,Value="$INSTANCE_ID"   --alarm-actions "$SNS_TOPIC_ARN"   --region "$AWS_REGION_VALUE"

aws cloudwatch put-metric-alarm   --alarm-name "dog-growth-journal-${INSTANCE_ID}-status-check"   --alarm-description "EC2 status check failed"   --metric-name StatusCheckFailed   --namespace AWS/EC2   --statistic Maximum   --period 60   --threshold 1   --comparison-operator GreaterThanOrEqualToThreshold   --evaluation-periods 1   --dimensions Name=InstanceId,Value="$INSTANCE_ID"   --alarm-actions "$SNS_TOPIC_ARN"   --region "$AWS_REGION_VALUE"

aws logs put-metric-filter   --log-group-name "$LOG_GROUP"   --filter-name dog-growth-journal-error-count   --filter-pattern 'ERROR'   --metric-transformations metricName=ErrorCount,metricNamespace=DogGrowthJournal,metricValue=1   --region "$AWS_REGION_VALUE"

aws cloudwatch put-metric-alarm   --alarm-name "dog-growth-journal-app-errors"   --alarm-description "Application errors detected in logs"   --metric-name ErrorCount   --namespace DogGrowthJournal   --statistic Sum   --period 300   --threshold 1   --comparison-operator GreaterThanOrEqualToThreshold   --evaluation-periods 1   --alarm-actions "$SNS_TOPIC_ARN"   --region "$AWS_REGION_VALUE"

echo "CloudWatch alarms and metric filter created."
