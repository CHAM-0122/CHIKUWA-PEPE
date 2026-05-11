# Dog Growth Journal

複数の犬のプロフィール、日次記録、写真を管理できる FastAPI アプリです。

## ローカル起動

1. `.env.example` を `.env` にコピーします。
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
- `scripts/ec2-bootstrap.sh`: Amazon Linux 2023 初期セットアップ
- `scripts/deploy-prod.sh`: 本番デプロイスクリプト
- `deploy/dog-growth-journal.service`: systemd 自動起動設定
- `docs/aws-ec2-deploy.md`: EC2 デプロイ手順

## ローカル確認

```bash
pytest
```

## AWS / EC2 デプロイ

概要は [docs/aws-ec2-deploy.md](docs/aws-ec2-deploy.md) を見てください。

最短手順は次です。

```bash
cp .env.production.example .env.production
./scripts/deploy-prod.sh
```
