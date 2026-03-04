import asyncio
from pyrogram import Client
from typing import Optional

async def live_progress_updater(
    bot: Client, 
    chat_id: int, 
    message_id: int,
    duration_seconds: int
) -> None:
    """
    Live progress bar updater for music playback.
    
    Args:
        bot: Pyrogram bot client
        chat_id: Chat ID where message is sent
        message_id: Message ID to edit
        duration_seconds: Total duration in seconds
    """
    try:
        # Parse duration
        if not duration_seconds or duration_seconds <= 0:
            return
            
        for elapsed in range(0, duration_seconds, 5):  # Update every 5 seconds
            await asyncio.sleep(5)
            
            # Calculate progress
            progress_percent = min((elapsed / duration_seconds) * 100, 100)
            filled_blocks = int(progress_percent / 5)
            bar = "█" * filled_blocks + "░" * (20 - filled_blocks)
            
            # Format time display
            elapsed_min = elapsed // 60
            elapsed_sec = elapsed % 60
            total_min = duration_seconds // 60
            total_sec = duration_seconds % 60
            
            progress_text = (
                f"🎵 **Now Playing**\n\n"
                f"[{bar}] {elapsed_min}:{elapsed_sec:02d} / {total_min}:{total_sec:02d}\n\n"
                f"⏳ Progress: {progress_percent:.1f}%"
            )
            
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=progress_text
                )
            except Exception:
                # Message edit failed (rate limit or message deleted)
                break
                
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


def parse_duration_to_seconds(duration_str: str) -> int:
    """Convert duration string (MM:SS or HH:MM:SS) to seconds."""
    if not duration_str or duration_str == "-":
        return 0
    
    try:
        parts = duration_str.split(":")
        if len(parts) == 2:  # MM:SS
            m, s = map(int, parts)
            return m * 60 + s
        elif len(parts) == 3:  # HH:MM:SS
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        else:
            return 0
    except Exception:
        return 0
