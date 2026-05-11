# AWS EC2 デプロイ手順

このプロジェクトは `EC2 1台 + Docker Compose + Nginx` 構成で公開する想定です。低コストで始めやすく、今のアプリ構成にそのまま合います。

## 1. AWS 側で用意するもの

- EC2 インスタンス 1 台
  - 推奨: Amazon Linux 2023
  - 用途: `app`, `db`, `nginx` を同居
- セキュリティグループ
  - `22/tcp`: 自分のIPだけ許可
  - `80/tcp`: 公開用に許可
  - `443/tcp`: HTTPS を使う場合に許可
- Elastic IP
  - 固定の公開 IPv4 を付ける

## 2. EC2 へ接続して初期セットアップ

```bash
ssh -i /path/to/your-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

```bash
git clone <YOUR_GIT_URL> CHIKUWA-PEPE
cd CHIKUWA-PEPE
./scripts/ec2-bootstrap.sh
```

`ec2-bootstrap.sh` 実行後は、`docker` グループ反映のため SSH し直してください。

## 3. 本番用環境変数を作る

```bash
cd ~/CHIKUWA-PEPE
cp .env.production.example .env.production
```

最低限この 2 つは必ず変更します。

- `DATABASE_URL` のパスワード部分
- `SECRET_KEY`

## 4. デプロイ

```bash
cd ~/CHIKUWA-PEPE
./scripts/deploy-prod.sh
```

これで本番用 Compose を使って `80` 番で起動します。

## 5. 起動確認

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml ps
curl http://localhost/healthz
```

外部からは次で確認できます。

```text
http://YOUR_ELASTIC_IP/
```

## 6. 再起動後も自動起動させる

```bash
sudo cp deploy/dog-growth-journal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dog-growth-journal.service
sudo systemctl start dog-growth-journal.service
sudo systemctl status dog-growth-journal.service
```

## 7. バックアップ対象

- Docker volume の PostgreSQL データ
- `~/CHIKUWA-PEPE/uploads/`
- `.env.production`

## 8. 次にやると良いこと

- 独自ドメインを Route 53 などで紐付ける
- HTTPS を入れる
- DB を将来 `RDS` に分離する
- `uploads/` を将来 `S3` に移す
