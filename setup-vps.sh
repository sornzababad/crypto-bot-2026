#!/bin/bash
# VPS setup script for crypto-bot-2026
# Run as root on a fresh DigitalOcean Ubuntu 22.04 droplet:
#   bash setup-vps.sh

set -e

echo "=== 1. System update ==="
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git

echo "=== 2. Create bot user ==="
id -u botuser &>/dev/null || useradd -m -s /bin/bash botuser

echo "=== 3. Clone repo ==="
sudo -u botuser bash -c "
  cd /home/botuser
  git clone https://github.com/sornzababad/crypto-bot-2026.git
  cd crypto-bot-2026
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
"

echo "=== 4. Create .env file ==="
echo ""
echo "NOW PASTE YOUR SECRETS into /home/botuser/crypto-bot-2026/.env"
echo "Copy the template:"
echo "  cp /home/botuser/crypto-bot-2026/.env.example /home/botuser/crypto-bot-2026/.env"
echo "  nano /home/botuser/crypto-bot-2026/.env"
echo ""
read -p "Press ENTER after you have saved the .env file..."

chmod 600 /home/botuser/crypto-bot-2026/.env
chown botuser:botuser /home/botuser/crypto-bot-2026/.env

echo "=== 5. Install systemd service ==="
cp /home/botuser/crypto-bot-2026/crypto-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable crypto-bot
systemctl start crypto-bot

echo ""
echo "=== Done! Bot is running. ==="
echo "Check status:  systemctl status crypto-bot"
echo "Watch logs:    journalctl -u crypto-bot -f"
