import asyncio
import sys
import logging
# guard against third-party 'queue' modules shadowing stdlib
sys.modules.pop("queue", None)
from pyrogram import idle
from app.config import API_ID, API_HASH, BOT_TOKEN, USER_SESSION
from app.user import create_user
from app.player import Player
from app.bot import create_bot

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("pyrogram").setLevel(logging.CRITICAL)
    logging.getLogger("pyrogram.dispatcher").setLevel(logging.CRITICAL)
    logging.getLogger("pyrogram.session").setLevel(logging.CRITICAL)
    if not API_ID or not API_HASH or not BOT_TOKEN or not USER_SESSION:
        raise RuntimeError("Missing API_ID, API_HASH, BOT_TOKEN or USER_SESSION in environment")
    user = create_user(USER_SESSION, API_ID, API_HASH)
    await user.start()
    player = Player(user)
    await player.start()
    try:
        bot = create_bot(API_ID, API_HASH, BOT_TOKEN, player)
        await bot.start()
    except Exception as e:
        import sqlite3
        if isinstance(e, sqlite3.OperationalError) and "database is locked" in str(e).lower():
            print("Database locked, trying alternative session...")
            # Remove problematic session files and retry
            import os
            alt_session_path = os.path.join(os.getcwd(), "sessions", "bot", "music-bot-alt.session")
            alt_journal_path = os.path.join(os.getcwd(), "sessions", "bot", "music-bot-alt.session-journal")
            if os.path.exists(alt_session_path):
                os.remove(alt_session_path)
            if os.path.exists(alt_journal_path):
                os.remove(alt_journal_path)
            bot = create_bot(API_ID, API_HASH, BOT_TOKEN, player, session_name="music-bot-alt")
            await bot.start()
        else:
            raise
    await idle()
    await bot.stop()
    await player.tgcalls.stop()
    await user.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
