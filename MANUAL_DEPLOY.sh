#!/bin/bash

# Manual Deployment Guide for Lily Music Bot
# Run these commands on your server after SSHing in

echo "=============================================="
echo "  🚀 Lily Music Bot - Manual Deploy Commands"
echo "=============================================="
echo ""
echo "Copy and run these commands on your server:"
echo "  ssh root@140.245.240.202"
echo ""

cat << 'EOF'

# Step 1: Connect to server
ssh root@140.245.240.202
# Password: Akshay343402355468

# Step 2: Navigate and pull latest code
cd /root/lily_music-
git pull origin main

# Step 3: Install dependencies
apt-get update && apt-get install -y python3 python3-pip python3-venv ffmpeg curl git

# Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Verify .env file exists
cat .env

# Step 5: Setup systemd service (if not already done)
cat > /etc/systemd/system/lily-music-bot.service << SERVICEEOF
[Unit]
Description=Lily Music Bot - Telegram Music Player
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/lily_music-
Environment="PATH=/root/lily_music-/venv/bin"
ExecStart=/root/lily_music-/venv/bin/python start_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lily-music-bot

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable lily-music-bot

# Step 6: Restart bot
systemctl restart lily-music-bot

# Step 7: Check status
systemctl status lily-music-bot

# View logs
journalctl -u lily-music-bot -f

EOF

echo ""
echo "=============================================="
echo "Quick Deploy (one-liner):"
echo "=============================================="
echo ""
echo "ssh root@140.245.240.202 'cd /root/lily_music- && git pull origin main && source venv/bin/activate && pip install -r requirements.txt -q && systemctl restart lily-music-bot && sleep 3 && systemctl status lily-music-bot'"
echo ""
