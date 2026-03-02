#!/usr/bin/env bash
set -euo pipefail

# Deploy PDU poller to a remote Linux box via SSH.
#
# Usage:
#   ./deploy.sh user@host            # deploy using existing .env on remote
#   ./deploy.sh user@host .env.prod  # deploy and copy a local .env file
#
# Prerequisites:
#   - SSH key access to the target box
#   - sudo privileges on the target (for systemd setup)

REMOTE="${1:?Usage: ./deploy.sh user@host [env-file]}"
ENV_FILE="${2:-}"
REMOTE_DIR="/opt/pdu"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Deploying PDU to ${REMOTE}:${REMOTE_DIR}"

# Ensure remote directory exists (ssh -t for sudo TTY)
ssh -t "$REMOTE" "sudo mkdir -p ${REMOTE_DIR} && sudo chown \$(whoami) ${REMOTE_DIR}"

# Sync project files (exclude local venv, .env, and caches)
rsync -avz --delete \
  --exclude '.venv/' \
  --exclude '.env' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "${SCRIPT_DIR}/" "${REMOTE}:${REMOTE_DIR}/"

# Copy .env if provided
if [[ -n "$ENV_FILE" ]]; then
  echo "==> Copying ${ENV_FILE} → ${REMOTE}:${REMOTE_DIR}/.env"
  scp "$ENV_FILE" "${REMOTE}:${REMOTE_DIR}/.env"
fi

# Install uv if not present, then sync deps
ssh "$REMOTE" bash -s <<'SETUP'
set -euo pipefail
cd /opt/pdu

# Ensure ~/.local/bin is in PATH (not set in non-interactive SSH sessions)
export PATH="$HOME/.local/bin:$PATH"

# Install uv if missing
if ! command -v uv &>/dev/null; then
  echo "==> Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Sync dependencies
echo "==> Running uv sync"
uv sync
SETUP

# Install or update systemd service (ssh -t for sudo TTY)
# Only copy + daemon-reload if the service file changed; always restart.
ssh -t "$REMOTE" "\
  if ! diff -q ${REMOTE_DIR}/pdu.service /etc/systemd/system/pdu.service &>/dev/null; then
    echo '==> Installing systemd service'
    sudo cp ${REMOTE_DIR}/pdu.service /etc/systemd/system/pdu.service
    sudo systemctl daemon-reload
    sudo systemctl enable pdu
  fi
  echo '==> Restarting pdu service'
  sudo systemctl restart pdu
  echo '==> Done! Service status:'
  sudo systemctl status pdu --no-pager || true"

echo "==> Deploy complete: ${REMOTE}"
