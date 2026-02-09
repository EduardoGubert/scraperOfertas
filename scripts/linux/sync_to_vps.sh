#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

VPS_USER="root"
VPS_HOST="seu-ip-ou-dominio"
VPS_PATH="/opt/scraper-ml"
SSH_KEY=""

COOKIES_DIR="ml_browser_data"
ZIP_FILE="ml_cookies_export.tar.gz"

if [ ! -d "$COOKIES_DIR" ]; then
  echo "Cookies folder not found. Run: python -m apps.scraper.login_local"
  exit 1
fi

if [ "$VPS_HOST" = "seu-ip-ou-dominio" ]; then
  read -r -p "VPS host: " VPS_HOST
  read -r -p "VPS user: " VPS_USER
  read -r -p "VPS path: " VPS_PATH
fi

rm -f "$ZIP_FILE"
tar -czf "$ZIP_FILE" "$COOKIES_DIR"

SCP_CMD="scp"
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
  SCP_CMD="scp -i $SSH_KEY"
  SSH_CMD="ssh -i $SSH_KEY"
fi

$SCP_CMD "$ZIP_FILE" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/"
$SSH_CMD "${VPS_USER}@${VPS_HOST}" "cd $VPS_PATH && rm -rf ml_browser_data.bak && mv ml_browser_data ml_browser_data.bak 2>/dev/null; tar -xzf $ZIP_FILE && chmod -R 755 ml_browser_data"

echo "Sync complete."
