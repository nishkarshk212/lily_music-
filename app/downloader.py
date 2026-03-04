import asyncio
from typing import Optional, Tuple
from yt_dlp import YoutubeDL
import logging
import random

logger = logging.getLogger(__name__)

# List of Invidious instances as fallback for YouTube
INVIDIOUS_INSTANCES = [
    "https://invidious.io.lol",
    "https://inv.tux.pizza", 
    "https://yt.artemislena.eu",
    "https://invidious.tiekoetter.com",
]

def get_invidious_url():
    """Get a random working Invidious instance"""
    return random.choice(INVIDIOUS_INSTANCES)

AUDIO_YDL_OPTS = {
    "format": "bestaudio[ext=webm]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "skip_download": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extractor_args": {
        "youtube": {
            "skip": ["hls", "dash"],
            "player_client": "tv_embedded",
            "player_skip": ["webpage"]
        }
    },
    "check_formats": "selected",
    "youtube_include_dash_manifest": False,
    "youtube_include_hls_manifest": False,
    "socket_timeout": 30,
    "retries": 3,
    # Use TV embedded client (less restrictions)
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "referer": "https://www.youtube.com/",
    # Try without browser cookies first
    "prefer_free_formats": False,
    # Additional bypass techniques
    "extractor_retries": 3,
    "http_headers": {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
        "Sec-Fetch-Mode": "navigate",
    },
}

# Fallback options with Invidious
AUDIO_YDL_OPTS_FALLBACK = {
    "format": "bestaudio[ext=webm]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "skip_download": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extractor_args": {
        "youtube": {
            "skip": ["hls", "dash"],
            "player_client": "android",
            "player_skip": ["webpage"]
        }
    },
    "socket_timeout": 30,
    "retries": 2,
    "user_agent": "com.google.android.youtube/17.31.35 (Linux; U; Android 13) gzip",
    "referer": "https://www.youtube.com/",
    "http_headers": {
        "Accept": "*/*",
        "X-Goog-Api-Format-Version": "2",
    },
}

QUALITY_FORMATS = {
    "240": "bestvideo[height<=?240]+bestaudio/best",
    "360": "bestvideo[height<=?360]+bestaudio/best",
    "480": "bestvideo[height<=?480]+bestaudio/best",
    "720": "bestvideo[height<=?720]+bestaudio/best",
}

def _format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "-"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def _human_views(n: Optional[int]) -> str:
    if n is None:
        return "-"
    n = int(n)
    for unit in ["", "K", "M", "B", "T"]:
        if abs(n) < 1000:
            return f"{n}{unit}"
        n //= 1000
    return str(n)

async def resolve(query: str) -> Tuple[str, str, Optional[str], Optional[str], str, str]:
    def _extract() -> Tuple[str, str, Optional[str], Optional[str], str, str]:
        # Try primary method first
        try:
            with YoutubeDL(AUDIO_YDL_OPTS) as ydl:
                info = ydl.extract_info(query, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                url = info.get("url") or info.get("webpage_url")
                title = info.get("title") or "Audio"
                thumb = info.get("thumbnail")
                vid = info.get("id")
                duration_str = _format_duration(info.get("duration"))
                views_str = _human_views(info.get("view_count"))
                return url, title, thumb, vid, views_str, duration_str
        except Exception as e:
            logger.warning(f"Primary extraction failed: {e}")
            
            # Fallback: Try with Invidious instance
            try:
                invidious_url = get_invidious_url()
                logger.info(f"Trying Invidious fallback: {invidious_url}")
                
                opts = AUDIO_YDL_OPTS_FALLBACK.copy()
                opts["extractor_args"] = {
                    "youtube": {
                        "skip": ["hls", "dash"],
                        "player_client": "ios"
                    }
                }
                
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                    url = info.get("url") or info.get("webpage_url")
                    title = info.get("title") or "Audio"
                    thumb = info.get("thumbnail")
                    vid = info.get("id")
                    duration_str = _format_duration(info.get("duration"))
                    views_str = _human_views(info.get("view_count"))
                    logger.info(f"Invidious fallback successful: {title}")
                    return url, title, thumb, vid, views_str, duration_str
            except Exception as fallback_error:
                logger.error(f"Invidious fallback also failed: {fallback_error}")
                raise Exception(f"Yououtube blocked (bot detection). Try again or use different query. Error: {e}")
    
    return await asyncio.to_thread(_extract)
