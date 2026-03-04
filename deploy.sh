#!/bin/bash

# Lily Music Bot - Automated Deployment Script
# Repository: https://github.com/nishkarshk212/lily_music-.git

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=============================================="
echo "  🚀 Lily Music Bot Deployment"
echo "=============================================="
echo ""
echo "Server: root@140.245.240.202"
echo "Repository: https://github.com/nishkarshk212/lily_music-.git"
echo ""

# Function to run commands on server
run_on_server() {
    ssh root@140.245.240.202 "$1"
}

echo -e "${YELLOW}Step 1/4: Cloning/Pulling repository on server...${NC}"
run_on_server << 'ENDSSH'
cd /root || exit 1

if [ -d "lily_music-" ]; then
    echo "  ✓ Directory exists, pulling latest code..."
    cd lily_music-
    git fetch origin
    git reset --hard origin/main
    git pull origin main
else
    echo "  Cloning repository..."
    git clone https://github.com/nishkarshk212/lily_music-.git
    cd lily_music-
fi
ENDSSH

echo -e "${GREEN}✓ Repository updated${NC}"
echo ""

echo -e "${YELLOW}Step 2/4: Installing dependencies...${NC}"
run_on_server << 'ENDSSH'
cd /root/lily_music- || exit 1

# Install system dependencies if not present
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg curl git > /dev/null 2>&1

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
ENDSSH

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

echo -e "${YELLOW}Step 3/4: Configuring environment...${NC}"
run_on_server << 'ENDSSH'
cd /root/lily_music- || exit 1

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "  Creating .env file..."
    cat > .env << EOF
API_ID=33830507
API_HASH=54e1e0d86c6c2768b65dc945bb2096c7
BOT_TOKEN=8775908280:AAFNQ9FeFpxCTapH9FIP0HguTXEI4rvcfeo
PHONE=+917992460285
USER_SESSION=BQIENmsAXt7OIKMQhvbavn5HeHxfDsiOw-kIl6DESUIoh2QXsf6ZOEaV0qsh4QijKQq0_KmqEbCmgtd5MtlQ5xsO1-g-ovxxqWSu-xmGqPzXiAL5BnX__ZDHo7a5aOzk-dnkVeAMOCHNSqs-earnOY8y18XRYtAv68269KjzgaGUntoTdzV-1xkA1ZhcBiO_fzlziMSv2qAtPDIcpG_NaKEEw9Kpows0EQjx-jheMeQKpVXQx2nIEjo1dQ3Is4YSMZSQBEKN2gjBZ28q_A1fk-qXLL5GCwpgIKTN3dxoBYmgcfMrOtlUkIRKZMPM3aYRkY_ibbUkenBMWJL7R_KVPFnXDdwgrQAAAAHti-7sAA
STICKER_SET_URL=https://t.me/addstickers/BurntxMini_by_stickersthiefbot
STICKER_SET_URLS=https://t.me/addstickers/BurntxMini_by_stickersthiefbot
STICKER_RANDOM_ENABLED=1
PROMO_ENABLED=1
PROMO_CHANNEL=https://t.me/Titanic_world_chatting_zonee
PROMO_INTERVAL=3600
EOF
    echo "  ✓ .env created"
else
    echo "  ✓ .env already exists"
fi
ENDSSH

echo -e "${GREEN}✓ Environment configured${NC}"
echo ""

echo -e "${YELLOW}Step 4/4: Setting up systemd service and starting bot...${NC}"
run_on_server << 'ENDSSH'
cd /root/lily_music- || exit 1

# Create systemd service
cat > /etc/systemd/system/lily-music-bot.service << EOF
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
EOF

systemctl daemon-reload
systemctl enable lily-music-bot > /dev/null 2>&1

echo "  Starting bot service..."
systemctl restart lily-music-bot
sleep 5
ENDSSH

echo -e "${GREEN}✓ Service configured and started${NC}"
echo ""

echo "=============================================="
echo -e "${GREEN}  ✅ DEPLOYMENT COMPLETE!${NC}"
echo "=============================================="
echo ""

# Check bot status
echo -e "${YELLOW}Bot Status:${NC}"
run_on_server "systemctl is-active lily-music-bot" || echo "Checking status..."

echo ""
echo -e "${YELLOW}Recent logs:${NC}"
run_on_server "journalctl -u lily-music-bot -n 10 --no-pager" || echo "Unable to fetch logs"

echo ""
echo "=============================================="
echo "Useful Commands:"
echo "  Check status:  ssh root@140.245.240.202 'systemctl status lily-music-bot'"
echo "  View logs:     ssh root@140.245.240.202 'journalctl -u lily-music-bot -f'"
echo "  Restart:       ssh root@140.245.240.202 'systemctl restart lily-music-bot'"
echo "=============================================="
echo ""
echo -e "${GREEN}Test the bot in Telegram:${NC}"
echo "  1. Send /start to check if bot is alive"
echo "  2. Join a voice chat"
echo "  3. Send /play <song name>"
echo ""
