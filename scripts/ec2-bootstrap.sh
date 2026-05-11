#!/usr/bin/env bash
set -euo pipefail

sudo yum update -y
sudo yum install -y git docker
sudo yum install -y docker-compose-plugin || true
sudo systemctl enable docker
sudo service docker start
sudo usermod -a -G docker ec2-user

echo "Checking Docker..."
docker --version

echo "Checking Docker Compose..."
if docker compose version >/dev/null 2>&1; then
  docker compose version
else
  echo "Docker Compose plugin is not available yet. Install docker-compose-plugin following Docker's Linux plugin docs, then rerun this check."
  exit 1
fi

echo "Reconnect your SSH session once so the docker group takes effect for ec2-user."
