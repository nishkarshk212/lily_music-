#!/bin/bash

# Simple Deploy Script for Lily Music Bot
# Repository: https://github.com/nishkarshk212/lily_music-.git

echo "=============================================="
echo "  🚀 Deploy Lily Music Bot to Server"
echo "=============================================="
echo ""
echo "Server: root@140.245.240.202"
echo "Repo: https://github.com/nishkarshk212/lily_music-.git"
echo ""

# Run commands on server
ssh root@140.245.240.202 << 'EOF'
set -e

echo "📥 Step 1: Pulling latest code from GitHub..."
cd /root/lily_music- || { echo "Bot directory not found!"; exit 1; }
git pull origin main

echo ""
echo "🔄 Step 2: Restarting bot service..."
systemctl restart lily-music-bot

sleep 3

echo ""
echo "✅ Step 3: Checking bot status..."
BOT_STATUS=$(systemctl is-active lily-music-bot)
if [ "$BOT_STATUS" = "active" ]; then
    echo "✅ Bot is RUNNING"
else
    echo "⚠️  Bot status: $BOT_STATUS"
fi

echo ""
echo "📋 Recent logs:"
journalctl -u lily-music-bot -n 15 --no-pager

echo ""
echo "=============================================="
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "Test the bot in Telegram:"
echo "  1. Send /health to check status"
echo "  2. Join a voice chat"
echo "  3. Send /play <song name>"
echo ""
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment completed successfully!"
else
    echo ""
    echo "❌ Deployment failed. Please check SSH connection and try again."
fi
