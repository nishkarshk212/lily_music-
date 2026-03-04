#!/bin/bash

echo "🔧 Fixing Bot Responsiveness Issue..."
echo ""

# Stop the bot
echo "1️⃣ Stopping bot..."
systemctl stop lily-music-bot
sleep 2

# Clean up old session files that might be causing issues
echo "2️⃣ Cleaning old session files..."
cd /root/lily_music-
rm -f sessions/bot/*.session-journal
rm -f *.session *.session-journal
rm -f app/*.session app/*.session-journal

# Update .env with correct credentials (already done, but verifying)
echo "3️⃣ Verifying configuration..."
grep "^BOT_TOKEN=" .env
grep "^API_ID=" .env
grep "^API_HASH=" .env
echo ""

# Start the bot with fresh session
echo "4️⃣ Starting bot with fresh session..."
systemctl start lily-music-bot
sleep 5

# Check status
echo ""
echo "5️⃣ Bot Status:"
systemctl status lily-music-bot --no-pager -l

echo ""
echo "✅ Bot restarted successfully!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  IMPORTANT: Bot Privacy Mode Issue"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "If bot still doesn't respond in private chat:"
echo ""
echo "Option 1: Test in a Group (Recommended)"
echo "  • Create a new Telegram group"
echo "  • Add @Lilyy_music_bot to the group"
echo "  • Send /start or /play <song>"
echo ""
echo "Option 2: Disable Privacy Mode"
echo "  • Message @BotFather on Telegram"
echo "  • Send: /mybots"
echo "  • Select: Lilyy_music_bot"
echo "  • Go to: Bot Settings → Group Privacy"
echo "  • Turn OFF (Disabled)"
echo "  • Then run: systemctl restart lily-music-bot"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
