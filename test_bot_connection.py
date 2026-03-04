#!/usr/bin/env python3
"""Quick test to verify bot is receiving messages"""
import asyncio
from pyrogram import Client
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
import os
import sys
sys.path.insert(0, os.getcwd())
from app.config import API_ID, API_HASH, BOT_TOKEN, USER_SESSION

async def test_bot():
    print("Testing bot connection...")
    
    # Test user client
    print("\n1. Testing USER_SESSION...")
    try:
        user = Client("test_user", api_id=API_ID, api_hash=API_HASH, session_string=USER_SESSION)
        await user.start()
        me = await user.get_me()
        print(f"✅ User client working! Logged in as: {me.first_name} (@{me.username or 'no username'})")
        await user.stop()
    except Exception as e:
        print(f"❌ User client failed: {e}")
        return
    
    # Test bot client
    print("\n2. Testing BOT_TOKEN...")
    try:
        bot = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        await bot.start()
        me = await bot.get_me()
        print(f"✅ Bot token working! Bot name: {me.first_name} (@{me.username})")
        
        # Get bot info
        info = await bot.get_chat(me.id)
        print(f"   - Can join groups: {info.can_join_groups}")
        print(f"   - Can read messages: {info.can_read_all_group_messages}")
        
        await bot.stop()
    except Exception as e:
        print(f"❌ Bot token failed: {e}")
        return
    
    print("\n✅ All connections verified!")
    print("\nIf both tests pass but bot doesn't respond, the issue is likely:")
    print("  - Bot privacy mode blocking messages")
    print("  - Bot needs to be added to a group first")
    print("  - Message handlers not properly configured")

if __name__ == "__main__":
    asyncio.run(test_bot())
