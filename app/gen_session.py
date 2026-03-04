#!/usr/bin/env python3
import os
import sys
import asyncio
from dotenv import load_dotenv

# guard against third-party 'queue' modules shadowing stdlib
sys.modules.pop("queue", None)
from pyrogram import Client

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")

async def main():
    if not API_ID or not API_HASH:
        print("Missing API_ID or API_HASH")
        return
    
    # Clean up any existing session files to avoid AUTH_KEY_DUPLICATED error
    session_name = "user_session_gen_fresh"
    session_files = [
        f"{session_name}.session",
        f"{session_name}.session-journal"
    ]
    
    for session_file in session_files:
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                print(f"Removed old session file: {session_file}")
            except Exception as e:
                print(f"Warning: Could not remove {session_file}: {e}")
    
    app = Client(session_name, api_id=API_ID, api_hash=API_HASH)
    print("Logging in to Telegram. You'll be asked for phone/code in the terminal.")
    print(f"Using phone number: {PHONE}")
    await app.start()
    s = await app.export_session_string()
    print("\n" + "="*60)
    print("YOUR SESSION STRING:")
    print("="*60)
    print(s)
    print("="*60)
    print("\nCopy this session string and add it to your .env file as USER_SESSION")
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
