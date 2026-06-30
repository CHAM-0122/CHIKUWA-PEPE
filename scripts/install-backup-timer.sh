#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-$HOME/CHIKUWA-PEPE}"
cd "$APP_DIR"

sudo cp deploy/dog-growth-journal-backup.service /etc/systemd/system/
sudo cp deploy/dog-growth-journal-backup.timer /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/dog-growth-journal-backup.service /etc/systemd/system/dog-growth-journal-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now dog-growth-journal-backup.timer
sudo systemctl start dog-growth-journal-backup.service
sudo systemctl status dog-growth-journal-backup.timer --no-pager
sudo systemctl list-timers dog-growth-journal-backup.timer --all --no-pager
