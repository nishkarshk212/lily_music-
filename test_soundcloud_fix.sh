#!/bin/bash
# Test SoundCloud playback fix

echo "🔍 Checking if player.py has SoundCloud download logic..."
cd /root/lily_music-

if grep -q "soundcloud.com" app/player.py; then
    echo "✅ Player has SoundCloud detection"
else
    echo "❌ Player missing SoundCloud detection!"
    echo "Current player.py _play method:"
    grep -A 20 "async def _play" app/player.py | head -25
fi

echo ""
echo "📊 Last 30 log entries:"
journalctl -u lily-music-bot -n 30 --no-pager

echo ""
echo "🔄 Restarting bot to apply any changes..."
systemctl restart lily-music-bot
sleep 3

echo ""
echo "✅ Bot restarted. Try playing a song now!"
