# AWS 監視・ログ保管

この構成では、運用しやすさを優先して次の流れを採用します。

- コンテナログは `CloudWatch Logs` に送る
- 通知は `CloudWatch Alarm + SNS` を使う
- 長期保管は `CloudWatch Logs -> S3 export` を使う

## 1. 事前準備

### IAM ロール
EC2 にアタッチする IAM ロールへ、[infra/iam/ec2-observability-policy.json](../infra/iam/ec2-observability-policy.json) 相当の権限を付けます。

### `.env.production`
次の値を追加します。

```env
AWS_REGION=ap-northeast-1
CLOUDWATCH_LOG_GROUP=/dog-growth-journal/prod
S3_LOG_ARCHIVE_BUCKET=your-log-archive-bucket
```

## 2. CloudWatch Logs を有効化したデプロイ

```bash
docker compose   --env-file .env.production   -f docker-compose.yml   -f docker-compose.prod.yml   -f docker-compose.logs.yml   up -d --build
```

ログ確認例:

```bash
aws logs tail /dog-growth-journal/prod --follow --region ap-northeast-1
```

## 3. ロググループ作成と保持期間設定

```bash
./scripts/setup-observability.sh "$HOME/CHIKUWA-PEPE" 30
```

## 4. 基本アラーム作成

事前に SNS トピックを 1 つ作成して、メール購読を追加します。

```bash
./scripts/create-basic-alarms.sh "$HOME/CHIKUWA-PEPE" i-xxxxxxxxxxxxxxxxx arn:aws:sns:ap-northeast-1:123456789012:dog-growth-journal-alerts
```

作成されるもの:

- EC2 CPU 高負荷アラーム
- EC2 ステータスチェック失敗アラーム
- CloudWatch Logs の `ERROR` 検知アラーム

## 5. S3 へログを退避

直近 24 時間分を S3 へ export:

```bash
./scripts/export-logs-to-s3.sh "$HOME/CHIKUWA-PEPE" 24
```

S3 内の保存先イメージ:

```text
s3://your-log-archive-bucket/cloudwatch-export/YYYY/MM/DD/
```

## 6. 運用のおすすめ

- CloudWatch Logs retention は 30 日か 90 日
- S3 はライフサイクルルールで長期保管へ移行
- SNS 通知先はメールか Chatbot/Slack
- 週次または日次で `export-logs-to-s3.sh` を cron 実行


## 7. 日常運用コマンド

本番状態の確認:

```bash
./scripts/check-prod.sh "$HOME/CHIKUWA-PEPE"
```

DB とアップロード画像のバックアップ:

```bash
./scripts/backup-prod.sh "$HOME/CHIKUWA-PEPE" 7
```

`backups/YYYYMMDD-HHMMSS/` に次が作成されます。

- `database.sql`
- `uploads.tar.gz`
- `README.txt`

## 8. 運用のおすすめ

- `check-prod.sh` を障害時の一次確認に使う
- `backup-prod.sh` を cron か systemd timer で日次実行する
- バックアップディレクトリごと S3 へ同期する場合は `aws s3 sync backups/ s3://your-backup-bucket/` を使う
- `docker compose ps` だけでなく `healthz` も毎回確認する


## 9. 自動バックアップ

日次バックアップを `systemd timer` で有効化:

```bash
./scripts/install-backup-timer.sh "$HOME/CHIKUWA-PEPE"
```

既定では毎日 `03:15` 頃にバックアップします。`RandomizedDelaySec=10m` があるため、実際の実行は少し前後します。

状態確認:

```bash
sudo systemctl status dog-growth-journal-backup.timer --no-pager
sudo systemctl list-timers dog-growth-journal-backup.timer --all --no-pager
```

手動実行:

```bash
sudo systemctl start dog-growth-journal-backup.service
```
