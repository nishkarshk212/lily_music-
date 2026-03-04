#!/bin/bash

# Lily Music Bot Deployment Script
# Server: 140.245.240.202
# User: root
# Port: 22

set -e

echo "======================================"
echo "Lily Music Bot Deployment"
echo "======================================"

# Configuration
SERVER_IP="140.245.240.202"
SERVER_USER="root"
SERVER_PORT="22"
REPO_URL="https://github.com/nishkarshk212/lily_music-.git"
BOT_DIR="/root/lily_music-"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment...${NC}"

# Step 1: Clone repository
echo -e "${YELLOW}Step 1: Cloning repository...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root
if [ -d "lily_music-" ]; then
    echo "Directory exists, pulling latest changes..."
    cd lily_music-
    git pull origin main
else
    echo "Cloning repository..."
    git clone $REPO_URL
    cd lily_music-
fi
ENDSSH

# Step 2: Install system dependencies
echo -e "${YELLOW}Step 2: Installing system dependencies...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root/lily_music-
apt-get update
apt-get install -y python3 python3-pip python3-venv ffmpeg curl git
ENDSSH

# Step 3: Setup Python virtual environment
echo -e "${YELLOW}Step 3: Setting up Python virtual environment...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root/lily_music-
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
ENDSSH

# Step 4: Install Python dependencies
echo -e "${YELLOW}Step 4: Installing Python dependencies...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root/lily_music-
source venv/bin/activate
pip install -r requirements.txt
ENDSSH

# Step 5: Create .env file
echo -e "${YELLOW}Step 5: Creating .env configuration...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root/lily_music-
cat > .env << EOF
API_ID=33830507
API_HASH=54e1e0d86c2768b65dc945bb2096c7
BOT_TOKEN=8775908280:AAFNQ9FeFpxCTapH9FIP0HguTXEI4rvcfeo
PHONE=+917992460285
USER_SESSION=
STICKER_SET_URL=https://t.me/addstickers/BurntxMini_by_stickersthiefbot
STICKER_SET_URLS=https://t.me/addstickers/BurntxMini_by_stickersthiefbot
STICKER_RANDOM_ENABLED=1
PROMO_ENABLED=1
PROMO_CHANNEL=https://t.me/Titanic_world_chatting_zonee
PROMO_INTERVAL=3600
EOF
echo ".env file created successfully"
ENDSSH

# Step 6: Generate user session (if needed)
echo -e "${YELLOW}Step 6: Checking user session...${NC}"
echo -e "${RED}NOTE: You need to generate USER_SESSION manually if not already set${NC}"
echo -e "${YELLOW}To generate session, run:${NC}"
echo "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP"
echo "  cd /root/lily_music-"
echo "  source venv/bin/activate"
echo "  python app/gen_session.py"

# Step 7: Create systemd service
echo -e "${YELLOW}Step 7: Creating systemd service...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cat > /etc/systemd/system/lily-music-bot.service << EOF
[Unit]
Description=Lily Music Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/lily_music-
Environment="PATH=/root/lily_music-/venv/bin"
ExecStart=/root/lily_music-/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable lily-music-bot
echo "Systemd service created successfully"
ENDSSH

# Step 8: Start the bot
echo -e "${YELLOW}Step 8: Starting the bot...${NC}"
ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /root/lily_music-
# Check if USER_SESSION is set
if grep -q "USER_SESSION=" .env && ! grep -q "USER_SESSION=$" .env; then
    echo "USER_SESSION found, starting bot..."
    systemctl start lily-music-bot
    systemctl status lily-music-bot --no-pager
else
    echo -e "${RED}USER_SESSION not set! Please generate it first.${NC}"
    echo "Run: python app/gen_session.py"
fi
ENDSSH

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "To check bot status:"
echo "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP 'systemctl status lily-music-bot'"
echo ""
echo "To view logs:"
echo "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP 'journalctl -u lily-music-bot -f'"
echo ""
echo "To restart bot:"
echo "  ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP 'systemctl restart lily-music-bot'"
echo ""
echo -e "${YELLOW}IMPORTANT: If USER_SESSION is empty, you need to generate it:${NC}"
echo "  1. SSH into server: ssh -p $SERVER_PORT $SERVER_USER@$SERVER_IP"
echo "  2. Navigate: cd /root/lily_music-"
echo "  3. Activate venv: source venv/bin/activate"
echo "  4. Generate session: python app/gen_session.py"
echo "  5. Update .env with the generated session"
echo "  6. Restart bot: systemctl restart lily-music-bot"
