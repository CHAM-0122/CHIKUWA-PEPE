#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/CHIKUWA-PEPE/certbot/www"

sudo docker run --rm   -v /etc/letsencrypt:/etc/letsencrypt   -v /var/lib/letsencrypt:/var/lib/letsencrypt   -v "$HOME/CHIKUWA-PEPE/certbot/www:/var/www/certbot"   certbot/certbot renew --webroot -w /var/www/certbot
