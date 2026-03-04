import asyncio
from pyrogram import Client
from pyrogram.types import Message
from datetime import datetime

class BotLogger:
    def __init__(self, bot_client: Client, log_channel: str):
        self.bot = bot_client
        self.channel = log_channel  # @log_x_bott or channel ID
    
    async def log_play(self, user_id: int, user_name: str, chat_id: int, chat_name: str, 
                       track_title: str, track_url: str, duration: str = "Unknown"):
        """Log when a user plays a song"""
        try:
            log_text = f"""
🎵 **New Play Request**

👤 User: {user_name} (`{user_id}`)
💬 Chat: {chat_name} (`{chat_id}`)
🎶 Track: {track_title}
⏱ Duration: {duration}
🔗 URL: `{track_url}`
🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            await self.bot.send_message(self.channel, log_text.strip())
        except Exception as e:
            print(f"Failed to log play: {e}")
    
    async def log_error(self, user_id: int, user_name: str, chat_id: int, 
                        error_type: str, error_msg: str, track_info: str = ""):
        """Log errors that occur during playback"""
        try:
            log_text = f"""
❌ **Playback Error**

👤 User: {user_name} (`{user_id}`)
💬 Chat: {chat_name} (`{chat_id}`)
🚫 Error Type: {error_type}
📝 Error: {error_msg}
{f'🎶 Track: {track_info}' if track_info else ''}
🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            await self.bot.send_message(self.channel, log_text.strip())
        except Exception as e:
            print(f"Failed to log error: {e}")
    
    async def log_download_start(self, user_id: int, user_name: str, query: str):
        """Log when download starts"""
        try:
            await self.bot.send_message(
                self.channel,
                f"⬇️ **Download Started**\n\n"
                f"👤 User: {user_name} (`{user_id}`)\n"
                f"🔍 Query: {query}\n"
                f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            print(f"Failed to log download: {e}")
    
    async def log_success(self, user_id: int, user_name: str, track_title: str):
        """Log successful playback start"""
        try:
            await self.bot.send_message(
                self.channel,
                f"✅ **Playing Successfully**\n\n"
                f"👤 User: {user_name} (`{user_id}`)\n"
                f"🎶 Track: {track_title}\n"
                f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            print(f"Failed to log success: {e}")
