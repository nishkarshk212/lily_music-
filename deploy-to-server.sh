#!/bin/bash

# Lily Music Bot - One-Click Server Deployment
# Run this script ON YOUR SERVER after SSHing in

set -e

echo "============================================================"
echo "  Lily Music Bot - Server Deployment"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1/7: Updating system packages...${NC}"
apt-get update -qq

echo -e "${YELLOW}Step 2/7: Installing system dependencies...${NC}"
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg curl git > /dev/null 2>&1
echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "${YELLOW}Step 3/7: Setting up project directory...${NC}"
cd /root
if [ -d "lily_music-" ]; then
    echo "  Pulling latest code from GitHub..."
    cd lily_music-
    git pull origin main > /dev/null 2>&1
else
    echo "  Cloning repository..."
    git clone https://github.com/nishkarshk212/lily_music-.git > /dev/null 2>&1
    cd lily_music-
fi
echo -e "${GREEN}✓ Repository ready${NC}"

echo -e "${YELLOW}Step 4/7: Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
echo -e "${GREEN}✓ Virtual environment ready${NC}"

echo -e "${YELLOW}Step 5/7: Installing Python dependencies...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo -e "${YELLOW}Step 6/7: Creating .env configuration...${NC}"
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
echo -e "${GREEN}✓ Configuration created${NC}"

echo -e "${YELLOW}Step 7/7: Creating systemd service...${NC}"
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
echo -e "${GREEN}✓ Systemd service configured${NC}"

echo ""
echo "============================================================"
echo -e "${GREEN}  ✓ Deployment Complete!${NC}"
echo "============================================================"
echo ""
echo "Starting bot service..."
systemctl start lily-music-bot
sleep 3

echo ""
echo "Bot Status:"
systemctl status lily-music-bot --no-pager
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Check status:  systemctl status lily-music-bot"
echo "  View logs:     journalctl -u lily-music-bot -f"
echo "  Restart:       systemctl restart lily-music-bot"
echo "  Stop:          systemctl stop lily-music-bot"
echo ""
echo -e "${GREEN}Your bot should now be running and responding to messages!${NC}"
echo ""
