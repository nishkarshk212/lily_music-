# 🚀 Lily Music Bot - Deployment Guide

## Server Information
- **IP Address**: 140.245.240.202
- **Username**: root
- **Port**: 22
- **Password**: Akshay343402355468

---

## Quick Deployment (Copy & Paste)

### Step 1: Connect to your server
```bash
ssh -p 22 root@140.245.240.202
# Enter password when prompted: Akshay343402355468
```

### Step 2: Clone and setup (run all commands on server)
```bash
# Navigate to root directory
cd /root

# Clone the repository
git clone https://github.com/nishkarshk212/lily_music-.git
cd lily_music-

# Install system dependencies
apt-get update && apt-get install -y python3 python3-pip python3-venv ffmpeg curl git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install Python packages
pip install -r requirements.txt
```

### Step 3: Create .env file
```bash
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
```

### Step 4: Generate USER_SESSION (REQUIRED!)
```bash
# Make sure you're still in the venv
python app/gen_session.py

# Follow the prompts:
# 1. Enter your phone number
# 2. Enter the verification code sent to Telegram
# 3. Copy the generated session string
# 4. Edit .env and paste it: nano .env
# 5. Find USER_SESSION= and paste your session after the =
# 6. Save (Ctrl+X, Y, Enter)
```

### Step 5: Create systemd service
```bash
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

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable lily-music-bot
```

### Step 6: Start the bot
```bash
# Start the service
systemctl start lily-music-bot

# Check status
systemctl status lily-music-bot

# View logs
journalctl -u lily-music-bot -f
```

---

## Management Commands

### Check bot status
```bash
systemctl status lily-music-bot
```

### View live logs
```bash
journalctl -u lily-music-bot -f
```

### Restart bot
```bash
systemctl restart lily-music-bot
```

### Stop bot
```bash
systemctl stop lily-music-bot
```

### Enable auto-start on boot
```bash
systemctl enable lily-music-bot
```

### Disable auto-start
```bash
systemctl disable lily-music-bot
```

---

## Troubleshooting

### Bot won't start?
Check the logs:
```bash
journalctl -u lily-music-bot --no-pager -n 50
```

### Common issues:

1. **"USER_SESSION not set"** - You need to generate it using `python app/gen_session.py`

2. **"Database locked"** - Delete the session files in `sessions/bot/` folder

3. **"Module not found"** - Reinstall dependencies: `pip install -r requirements.txt`

4. **"Port already in use"** - Another process is using the port, restart the service

---

## Verify Deployment

✅ Bot should be running if:
- `systemctl status lily-music-bot` shows "active (running)"
- Logs show successful startup messages
- Bot responds to Telegram commands

---

## Security Notes

⚠️ **Important**: 
- Keep your `.env` file secure and private
- Never commit `.env` to public repositories
- Regularly update your server: `apt-get update && apt-get upgrade`
- Monitor bot logs regularly for any issues

---

## Need Help?

If you encounter any issues during deployment, check:
1. All environment variables are correctly set in `.env`
2. USER_SESSION is properly generated
3. All dependencies are installed
4. Firewall allows necessary connections
5. Server has sufficient resources (RAM, CPU)
