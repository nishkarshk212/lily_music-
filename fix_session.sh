#!/bin/bash

# Fix session issue on server
echo "Fixing session authentication..."
echo ""

yes | ssh root@140.245.240.202 << 'ENDSSH'
cd /root/lily_music-

# Remove all session files
rm -rf sessions/
mkdir -p sessions/bot

# Use the existing USER_SESSION from .env
# Just need to restart the bot
systemctl restart lily-music-bot

sleep 5

echo ""
echo "Bot status:"
systemctl status lily-music-bot --no-pager

echo ""
echo "Recent logs:"
tail -20 bot.log

ENDSSH
