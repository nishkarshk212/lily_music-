#!/usr/bin/env python3
import asyncio
import sys
import os
import logging

# guard against third-party 'queue' modules shadowing stdlib
sys.modules.pop("queue", None)
from pyrogram import idle
from app.config import API_ID, API_HASH, BOT_TOKEN, USER_SESSION
from app.user import create_user
from app.player import Player
from app.bot import create_bot

async def main() -> None:
    # Setup comprehensive logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log')
        ]
    )
    
    print("="*60)
    print("Starting Lily Music Bot...")
    print("="*60)
    
    # Verify credentials
    print(f"API_ID: {API_ID}")
    print(f"API_HASH: {API_HASH[:10]}...{API_HASH[-10:] if len(API_HASH) > 20 else '***'}")
    print(f"BOT_TOKEN: {BOT_TOKEN[:20]}...{BOT_TOKEN[-10:] if len(BOT_TOKEN) > 30 else '***'}")
    print(f"USER_SESSION: {'Present' if USER_SESSION else 'MISSING!'}")
    print("="*60)
    
    if not API_ID or not API_HASH or not BOT_TOKEN or not USER_SESSION:
        logging.error("Missing required credentials!")
        raise RuntimeError("Missing API_ID, API_HASH, BOT_TOKEN or USER_SESSION in environment")
    
    try:
        # Start user client
        logging.info("Starting user client...")
        user = create_user(USER_SESSION, API_ID, API_HASH)
        await user.start()
        logging.info("User client started successfully!")
        
        # Start player
        logging.info("Initializing player...")
        player = Player(user)
        await player.start()
        logging.info("Player initialized!")
        
        # Start bot
        logging.info("Starting bot...")
        try:
            bot = create_bot(API_ID, API_HASH, BOT_TOKEN, player)
            await bot.start()
            logging.info("Bot started successfully!")
        except Exception as e:
            logging.error(f"Error starting bot: {e}")
            import sqlite3
            if isinstance(e, sqlite3.OperationalError) and "database is locked" in str(e).lower():
                logging.warning("Database locked, trying alternative session...")
                # Remove problematic session files and retry
                alt_session_path = os.path.join(os.getcwd(), "sessions", "bot", "music-bot-alt.session")
                alt_journal_path = os.path.join(os.getcwd(), "sessions", "bot", "music-bot-alt.session-journal")
                if os.path.exists(alt_session_path):
                    os.remove(alt_session_path)
                    logging.info(f"Removed {alt_session_path}")
                if os.path.exists(alt_journal_path):
                    os.remove(alt_journal_path)
                    logging.info(f"Removed {alt_journal_path}")
                bot = create_bot(API_ID, API_HASH, BOT_TOKEN, player, session_name="music-bot-alt")
                await bot.start()
                logging.info("Bot started with alternative session!")
            else:
                raise
        
        print("="*60)
        print("✅ Bot is now running and ready to respond!")
        print("Press Ctrl+C to stop the bot")
        print("="*60)
        
        # Keep the bot running
        await idle()
        
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        try:
            await bot.stop()
            await player.tgcalls.stop()
            await user.stop()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
