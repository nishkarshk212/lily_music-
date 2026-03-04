#!/bin/bash

# Lily Music Bot - Auto-Update & Self-Heal Script
# Runs every 6 hours to keep bot updated and healthy

set -e

LOG_FILE="/root/lily_music-/bot-autoupdate.log"
BOT_DIR="/root/lily_music-"
REPO_URL="https://github.com/nishkarshk212/lily_music-.git"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Starting Auto-Update & Health Check"
log "=========================================="

cd "$BOT_DIR" || exit 1

# Step 1: Stop the bot
log "Step 1: Stopping bot..."
systemctl stop lily-music-bot
sleep 2

# Step 2: Git pull latest changes
log "Step 2: Pulling latest updates from GitHub..."
git fetch origin main
if ! git diff --quiet HEAD origin/main; then
    log "Updates found! Pulling changes..."
    git pull origin main
    log "✓ Updates installed"
else
    log "✓ Already up to date"
fi

# Step 3: Clean old session files (prevent AUTH_KEY_DUPLICATED)
log "Step 3: Cleaning old session files..."
rm -f sessions/bot/*.session-journal
rm -f *.session *.session-journal
rm -f app/*.session app/*.session-journal
log "✓ Session files cleaned"

# Step 4: Verify .env exists and has required values
log "Step 4: Verifying configuration..."
if [ ! -f ".env" ]; then
    log "❌ ERROR: .env file missing!"
    exit 1
fi

missing_vars=()
grep -q "^API_ID=" .env || missing_vars+=("API_ID")
grep -q "^API_HASH=" .env || missing_vars+=("API_HASH")
grep -q "^BOT_TOKEN=" .env || missing_vars+=("BOT_TOKEN")
grep -q "^USER_SESSION=" .env || missing_vars+=("USER_SESSION")

if [ ${#missing_vars[@]} -gt 0 ]; then
    log "❌ ERROR: Missing environment variables: ${missing_vars[*]}"
    exit 1
fi
log "✓ Configuration verified"

# Step 5: Verify virtual environment
log "Step 5: Checking virtual environment..."
if [ ! -d "venv" ]; then
    log "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Step 6: Update dependencies if requirements.txt changed
log "Step 6: Checking Python dependencies..."
pip install -q -r requirements.txt
log "✓ Dependencies up to date"

# Step 7: Start the bot
log "Step 7: Starting bot..."
systemctl start lily-music-bot
sleep 5

# Step 8: Verify bot is running
log "Step 8: Verifying bot status..."
if systemctl is-active --quiet lily-music-bot; then
    log "✅ Bot is running successfully!"
    
    # Get bot status
    status=$(systemctl status lily-music-bot --no-pager -l | head -n 10)
    log "Bot Status:\n$status"
    
    # Check recent logs for errors
    recent_errors=$(journalctl -u lily-music-bot --since "2 minutes ago" --no-pager -p err -n 5)
    if [ -n "$recent_errors" ]; then
        log "⚠️  Recent errors detected:\n$recent_errors"
    else
        log "✓ No errors in recent logs"
    fi
else
    log "❌ Bot failed to start! Attempting recovery..."
    
    # Recovery: Try to diagnose the issue
    log "Checking logs..."
    journalctl -u lily-music-bot --no-pager -n 20 > /tmp/bot_error.log
    
    if grep -q "AuthKeyDuplicated" /tmp/bot_error.log; then
        log "Issue: AUTH_KEY_DUPLICATED detected"
        log "Cleaning session files and retrying..."
        rm -f sessions/bot/*.session* app/*.session* *.session*
        systemctl restart lily-music-bot
        sleep 3
        
        if systemctl is-active --quiet lily-music-bot; then
            log "✅ Recovery successful!"
        else
            log "❌ Recovery failed. Manual intervention required."
        fi
    elif grep -q "database is locked" /tmp/bot_error.log; then
        log "Issue: Database locked detected"
        log "Removing journal files..."
        rm -f sessions/bot/*.session-journal
        systemctl restart lily-music-bot
        sleep 3
        
        if systemctl is-active --quiet lily-music-bot; then
            log "✅ Recovery successful!"
        else
            log "❌ Recovery failed. Manual intervention required."
        fi
    else
        log "Unknown error. Check /tmp/bot_error.log for details"
    fi
fi

log "=========================================="
log "Auto-Update & Health Check Complete"
log "=========================================="
echo ""
