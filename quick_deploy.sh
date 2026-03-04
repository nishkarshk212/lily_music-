#!/bin/bash
# Quick deployment script for YouTube proxy fix

echo "🔄 Pulling latest changes from GitHub..."
cd /root/lily_music-
git pull origin main

echo "🔄 Restarting bot..."
systemctl restart lily-music-bot

echo "✅ Deployment complete!"
echo ""
echo "Try playing a song now with /play <song name>"
echo ""
echo "If it still fails, check logs with:"
echo "journalctl -u lily-music-bot -n 50 --no-pager"
