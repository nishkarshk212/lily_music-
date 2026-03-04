"""
Example: How to use the local download feature with progress tracking
"""

from app.downloader import download_audio_file, cleanup_file, resolve
from app.progress import live_progress_updater, parse_duration_to_seconds
from pyrogram import Client, filters
import os


async def progress_callback(percent: str, speed: str, eta: str):
    """Callback to update progress message"""
    # This will be called during download
    print(f"📥 Downloading: {percent} | ⚡ Speed: {speed} | ⏱ ETA: {eta}")
    # You can edit a Telegram message here to show live progress


async def play_with_download(client: Client, message):
    """
    Example play handler that downloads file locally first, then plays
    """
    query = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    
    if not query:
        await message.reply("❌ Please provide a song name or URL")
        return
    
    # Step 1: Send initial message
    status_msg = await message.reply("🔍 Searching and downloading...")
    
    try:
        # Step 2: Download audio file locally with progress tracking
        file_path, info = await download_audio_file(
            query, 
            progress_callback=progress_callback
        )
        
        # Get metadata
        title = info.get("title", "Unknown")
        duration = info.get("duration", 0)
        thumb_url = info.get("thumbnail", None)
        
        # Step 3: Update status
        await status_msg.edit(f"🎵 Downloaded: {title}\n⏳ Duration: {duration // 60}:{duration % 60:02d}")
        
        # Step 4: Join voice chat and play the file
        # Note: You'll need to integrate this with your player
        # Example:
        # from app.player import join_and_play
        # await join_and_play(tgcalls, message.chat.id, file_path)
        
        await status_msg.edit("✅ Now Playing in Voice Chat!")
        
        # Step 5: Optional - Start live progress updater
        # asyncio.create_task(live_progress_updater(
        #     client, 
        #     message.chat.id, 
        #     status_msg.id, 
        #     duration
        # ))
        
        # Step 6: Cleanup after playback (call this later)
        # cleanup_file(file_path)
        
    except Exception as e:
        await status_msg.edit(f"❌ Error: {str(e)}")
        # Cleanup on error
        if 'file_path' in locals():
            cleanup_file(file_path)


# Alternative: Use streaming method (current implementation)
async def play_with_streaming(client: Client, message):
    """
    Example play handler using direct streaming (no local download)
    This is what the current bot uses
    """
    query = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    
    if not query:
        await message.reply("❌ Please provide a song name or URL")
        return
    
    status_msg = await message.reply("🔍 Extracting audio...")
    
    try:
        # Get direct stream URL (no download)
        url, title, thumb, vid, views, duration = await resolve(query)
        
        await status_msg.edit(f"🎵 Found: {title}\n⏳ {duration}")
        
        # Play directly with stream URL
        # The player will handle streaming
        # pos = await player.enqueue(chat_id, (url, title, thumb, vid))
        
    except Exception as e:
        await status_msg.edit(f"❌ Error: {str(e)}")


# Handler examples
@filters.command("playlocal")
async def play_local_handler(client: Client, message):
    """Play using local download method"""
    await play_with_download(client, message)


@filters.command("playstream")
async def play_stream_handler(client: Client, message):
    """Play using streaming method (default)"""
    await play_with_streaming(client, message)
