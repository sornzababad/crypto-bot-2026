#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# VPS Setup Script — Crypto Trading Bot
# Run this ONE TIME on a fresh Ubuntu VPS as the ubuntu user (not root).
#
# Usage:
#   chmod +x setup_vps.sh
#   ./setup_vps.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$HOME/crypto-bot-2026"
SERVICE_NAME="crypto-bot"

echo "======================================================"
echo "  Crypto Trading Bot — VPS Setup"
echo "======================================================"

# ── 1. System packages ────────────────────────────────────────
echo ""
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git

# ── 2. Clone or pull latest code ──────────────────────────────
echo ""
echo "[2/6] Fetching latest code..."
if [ -d "$REPO_DIR/.git" ]; then
    git -C "$REPO_DIR" pull origin main
else
    git clone https://github.com/sornzababad/crypto-bot-2026.git "$REPO_DIR"
fi

# ── 3. Python virtual environment + dependencies ──────────────
echo ""
echo "[3/6] Setting up Python environment..."
python3 -m venv "$REPO_DIR/venv"
"$REPO_DIR/venv/bin/pip" install --upgrade pip -q
"$REPO_DIR/venv/bin/pip" install -r "$REPO_DIR/requirements.txt" -q

# ── 4. Environment file ───────────────────────────────────────
echo ""
echo "[4/6] Setting up environment variables..."
if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    echo ""
    echo "  *** ACTION REQUIRED ***"
    echo "  Fill in your API keys in: $REPO_DIR/.env"
    echo "  Run:  nano $REPO_DIR/.env"
    echo ""
    read -rp "  Press ENTER after editing .env to continue..." _
fi

# ── 5. Install systemd service ────────────────────────────────
echo ""
echo "[5/6] Installing systemd service..."

# Replace User= with actual current user
sed "s/^User=ubuntu/User=$(whoami)/" "$REPO_DIR/crypto-bot.service" \
  | sed "s|/home/ubuntu|$HOME|g" \
  > /tmp/${SERVICE_NAME}.service

sudo cp /tmp/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start  "$SERVICE_NAME"

# ── 6. Status check ───────────────────────────────────────────
echo ""
echo "[6/6] Checking service status..."
sleep 2
sudo systemctl status "$SERVICE_NAME" --no-pager || true

echo ""
echo "======================================================"
echo "  Setup complete!"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status $SERVICE_NAME       # is it running?"
echo "    sudo journalctl -u $SERVICE_NAME -f       # live logs"
echo "    sudo systemctl restart $SERVICE_NAME      # restart"
echo "    sudo systemctl stop $SERVICE_NAME         # stop"
echo "======================================================"
