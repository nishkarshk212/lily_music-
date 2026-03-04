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
    For SoundCloud, we download the file and return local path.
    
    Args:
        query: Song name to search OR SoundCloud URL
        
    Returns:
        Tuple of (file_path_or_url, title, thumbnail, video_id, views, duration)
    """
    def _extract() -> Tuple[str, str, Optional[str], Optional[str], str, str]:
        # SoundCloud options with better compatibility
        sc_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "scsearch",
            "extract_flat": False,
            "ignoreerrors": "only_download",
            "socket_timeout": 30,
            "retries": 2,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
            }
        }
        
        try:
            logger.info(f"🔍 Searching SoundCloud: {query[:50]}...")
            
            with YoutubeDL(sc_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                
                if not info:
                    raise Exception("No results from SoundCloud")
                
                # If it's a search result (playlist), get first track
                if "entries" in info and info["entries"]:
                    entries = list(info["entries"])
                    if not entries:
                        raise Exception("No tracks found")
                    info = entries[0]
                    logger.info(f"📊 Found {len(entries)} results, using: {info.get('title', 'Unknown')}")
                
                # Extract metadata
                url = info.get("url") or info.get("webpage_url")
                if not url:
                    raise Exception("No playable URL found")
                    
                title = info.get("title") or "Unknown Track"
                thumbnail = info.get("thumbnail") or info.get("artwork_url")
                video_id = str(info.get("id", f"sc_{hash(title)}"))
                duration = info.get("duration")
                play_count = info.get("playback_count", 0)
                
                # Format for display
                duration_str = _format_duration(duration)
                views_str = _human_views(play_count)
                
                logger.info(f"✅ Found: {title} | {duration_str}")
                
                # Return the direct URL - player will handle downloading if needed
                return url, title, thumbnail, video_id, views_str, duration_str
                
        except Exception as e:
            logger.error(f"❌ Extraction failed: {e.__class__.__name__}: {str(e)[:200]}")
            raise Exception(f"Could not find the song. Try a different name or check spelling.")
    
    return await asyncio.to_thread(_extract)


async def download_audio_file(url: str) -> Tuple[str, dict]:
    """
    Download audio file locally for processing.
    Uses ffmpeg for reliable downloading of streaming audio.
    
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
            if percent and speed:
                logger.info(f"⬇️  {percent.strip()} | {speed.strip()}")
        elif d["status"] == "finished":
            logger.info("✅ Download done")
    
    download_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_callback],
        "socket_timeout": 60,
        "retries": 3,
        "fragment_retries": 3,
        "continuedl": True,  # Resume interrupted downloads
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive",
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    
    def _download():
        try:
            with YoutubeDL(download_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                # Ensure mp3 format
                if file_path.endswith(".webm") or file_path.endswith(".m4a"):
                    file_path = file_path.rsplit(".", 1)[0] + ".mp3"
                return file_path, info
        except Exception as e:
            logger.error(f"❌ Download failed: {e.__class__.__name__}: {str(e)[:200]}")
            raise
    
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
