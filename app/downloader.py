"""
Audio downloader for Lily Music Bot - SoundCloud Optimized
Clean, simple, and reliable audio extraction from SoundCloud
"""

import asyncio
from typing import Optional, Tuple
from yt_dlp import YoutubeDL
import logging
import os
import uuid

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _format_duration(seconds: Optional[int]) -> str:
    """Format seconds to MM:SS or HH:MM:SS"""
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _human_views(n: Optional[int]) -> str:
    """Format view count to human readable (K, M, B)"""
    if n is None:
        return "0"
    n = int(n)
    for unit in ["", "K", "M", "B"]:
        if abs(n) < 1000:
            return f"{n}{unit}"
        n //= 1000
    return f"{n}T"


async def resolve(query: str) -> Tuple[str, str, Optional[str], Optional[str], str, str]:
    """
    Resolve query to audio stream URL using SoundCloud.
    
    Args:
        query: Song name to search OR SoundCloud URL
        
    Returns:
        Tuple of (url, title, thumbnail, video_id, views, duration)
    """
    def _extract() -> Tuple[str, str, Optional[str], Optional[str], str, str]:
        # SoundCloud options
        sc_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "default_search": "scsearch",  # Search SoundCloud
        }
        
        try:
            logger.info(f"🔍 Searching/Extracting from SoundCloud: {query[:50]}...")
            
            with YoutubeDL(sc_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                
                # If it's a search result (playlist), get first track
                if "entries" in info:
                    entries = list(info["entries"])
                    if not entries:
                        raise Exception("No results found on SoundCloud")
                    info = entries[0]
                    logger.info(f"📊 Found {len(entries)} results, using first match")
                
                # Extract metadata
                url = info.get("url")
                title = info.get("title") or "Unknown Track"
                thumbnail = info.get("thumbnail")
                video_id = info.get("id", f"sc_{hash(title)}")
                duration = info.get("duration")
                play_count = info.get("playback_count", 0)
                
                # Format for display
                duration_str = _format_duration(duration)
                views_str = _human_views(play_count)
                
                logger.info(f"✅ SoundCloud: {title} | Duration: {duration_str} | Views: {views_str}")
                
                return url, title, thumbnail, video_id, views_str, duration_str
                
        except Exception as e:
            logger.error(f"❌ SoundCloud extraction failed: {e}")
            raise Exception(
                f"Could not find/play the song. Please try:\n"
                f"• A different song name\n"
                f"• A direct SoundCloud URL (https://soundcloud.com/...)"
            )
    
    return await asyncio.to_thread(_extract)


async def download_audio_file(url: str) -> Tuple[str, dict]:
    """
    Download audio file locally for processing.
    
    Args:
        url: Audio stream URL from resolve()
        
    Returns:
        Tuple of (file_path, info_dict)
    """
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{unique_id}.%(ext)s")
    
    def progress_callback(d):
        """Track download progress"""
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A")
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")
            logger.info(f"⬇️  Downloading: {percent.strip()} | Speed: {speed.strip()} | ETA: {eta.strip()}")
        elif d["status"] == "finished":
            logger.info("✅ Download complete, processing...")
    
    download_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_callback],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    
    def _download():
        with YoutubeDL(download_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            # Convert to mp3 format
            file_path = file_path.rsplit(".", 1)[0] + ".mp3"
            return file_path, info
    
    return await asyncio.to_thread(_download)


def cleanup_file(file_path: str) -> bool:
    """Remove downloaded file after use"""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"🗑️  Cleaned up: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")
    return False
