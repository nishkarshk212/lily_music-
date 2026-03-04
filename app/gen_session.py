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
    app = Client("user_session_gen", api_id=API_ID, api_hash=API_HASH)
    print("Logging in to Telegram. You'll be asked for phone/code in the terminal.")
    await app.start()
    s = await app.export_session_string()
    print(s)
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
