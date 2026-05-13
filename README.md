# Dog Growth Journal

複数の犬のプロフィール、日次記録、写真を管理できる FastAPI アプリです。

## ローカル起動

1. `.env` を用意します。
2. 次のコマンドで起動します。

```bash
docker compose up --build
```

ブラウザで `http://localhost:8001` を開くとアプリを利用できます。

## 主な機能

- 犬プロフィールの登録、編集、削除
- 犬ごとの日次記録の登録、一覧、編集、削除
- 写真アップロードと差し替え時のファイル整理
- FastAPI の HTML 画面と API エンドポイント

## API

- `GET /api/dogs`
- `POST /api/dogs`
- `DELETE /api/dogs/{dog_id}`
- `POST /api/records`
- `DELETE /api/records/{record_id}`
- `POST /api/uploads`
- `GET /healthz`

## AWS 公開用ファイル

- `.env.production.example`: 本番用環境変数の雛形
- `docker-compose.prod.yml`: EC2 本番向けの Compose 上書き設定
- `docker-compose.https.yml`: HTTPS 有効化用の Compose 上書き設定
- `scripts/ec2-bootstrap.sh`: Amazon Linux 2023 初期セットアップ
- `scripts/deploy-prod.sh`: 本番デプロイスクリプト
- `scripts/request-cert.sh`: Let's Encrypt 証明書の初回取得
- `scripts/deploy-https.sh`: HTTPS 構成でのデプロイ
- `scripts/renew-cert.sh`: 証明書更新
- `deploy/dog-growth-journal.service`: systemd 自動起動設定
- `docs/aws-ec2-deploy.md`: EC2 デプロイ手順

## 本番設定のポイント

- `DATABASE_URL` と `POSTGRES_PASSWORD` は同じパスワードにそろえます。
- 本番では `docker compose --env-file .env.production` を使うため、`.env.production` だけでデプロイできます。
- `PUBLIC_PORT=80` で EC2 公開、ローカルでは `PUBLIC_PORT=8001` で利用できます。

## HTTPS 化

`chamcham.blog` などの独自ドメインを EC2 の Elastic IP に向けたあと、次の流れで HTTPS 化できます。

```bash
./scripts/request-cert.sh "$HOME/CHIKUWA-PEPE" chamcham.blog you@example.com
./scripts/deploy-https.sh
```

更新確認:

```bash
./scripts/renew-cert.sh
```

## ローカル確認

```bash
pytest
```

## AWS / EC2 デプロイ

概要は [docs/aws-ec2-deploy.md](docs/aws-ec2-deploy.md) を見てください。


## 監視・ログ保管

CloudWatch Logs と S3 を使う構成は [docs/aws-observability.md](docs/aws-observability.md) を見てください。
