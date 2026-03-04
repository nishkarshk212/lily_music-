#!/bin/bash

echo "=============================================="
echo "  Generate Fresh User Session on Server"
echo "=============================================="
echo ""
echo "This will generate a fresh USER_SESSION on the server."
echo "You'll need to enter your phone number and verification code."
echo ""
echo "Server: root@140.245.240.202"
echo "Password: Akshay343402355468"
echo ""
echo "Connecting to server..."
echo ""

ssh root@140.245.240.202 << 'ENDSSH'
cd /root/lily_music-

echo ""
echo "Stopping bot..."
systemctl stop lily-music-bot

echo ""
echo "Removing old sessions..."
rm -rf sessions/

echo ""
echo "Generating fresh user session..."
source venv/bin/activate
python app/gen_session.py

echo ""
echo "Session generated! Copy the session string above and update .env if needed."
echo ""
echo "Restarting bot..."
systemctl restart lily-music-bot

sleep 5

echo ""
echo "Bot status:"
systemctl status lily-music-bot --no-pager

echo ""
echo "Recent logs:"
tail -20 bot.log

ENDSSH
