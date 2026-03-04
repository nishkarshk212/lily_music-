#!/usr/bin/env python3
"""
Session Generator for Lily Music Bot
Generates Pyrogram session string with new API credentials
"""

import asyncio
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
import sys

# New API credentials
API_ID = 38548403
API_HASH = "4230e3ccece2002ebbf0984cb9ca6f85"

async def generate_session():
    print("=" * 60)
    print("  Lily Music Bot - Session Generator")
    print("=" * 60)
    print()
    print(f"API_ID: {API_ID}")
    print(f"API_HASH: {API_HASH}")
    print()
    
    # Create client
    app = Client(
        "user_session",
        api_id=API_ID,
        api_hash=API_HASH
    )
    
    await app.start()
    
    try:
        # Export session
        session_string = await app.export_session_string()
        
        print()
        print("=" * 60)
        print("  ✅ SESSION GENERATED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("Copy this session string:")
        print("-" * 60)
        print(session_string)
        print("-" * 60)
        print()
        print("NEXT STEPS:")
        print("1. Copy the session string above")
        print("2. Update your .env file:")
        print("   USER_SESSION=<paste_session_here>")
        print("3. Deploy to server")
        print()
        
        # Save to file
        with open("new_user_session.txt", "w") as f:
            f.write(session_string)
        print(f"💾 Session also saved to: new_user_session.txt")
        print()
        
    except SessionPasswordNeeded:
        print()
        print("⚠️  Two-Step Verification enabled!")
        password = input("Enter your 2FA password: ")
        await app.check_password(password)
        
        # Try again after password
        session_string = await app.export_session_string()
        print()
        print("=" * 60)
        print("  ✅ SESSION GENERATED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("Copy this session string:")
        print("-" * 60)
        print(session_string)
        print("-" * 60)
        print()
        
        # Save to file
        with open("new_user_session.txt", "w") as f:
            f.write(session_string)
        print(f"💾 Session saved to: new_user_session.txt")
        print()
    
    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print("\n\n❌ Generation cancelled!")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("\nMake sure you entered correct phone number and code.")
        sys.exit(1)
