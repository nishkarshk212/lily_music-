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
    "https://inv.nadeko.net",
    "https://yewtu.be",
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
            "player_client": "ios",
            "player_skip": ["webpage"]
        }
    },
    "check_formats": "selected",
    "youtube_include_dash_manifest": False,
    "youtube_include_hls_manifest": False,
    "socket_timeout": 30,
    "retries": 3,
    # Use iOS client (more reliable for avoiding bot detection)
    "user_agent": "com.google.ios.youtube/17.33.2 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "referer": "https://www.youtube.com/",
    "prefer_free_formats": False,
    "extractor_retries": 3,
    "http_headers": {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Goog-Api-Format-Version": "2",
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
            "player_client": "web_music",
            "player_skip": ["webpage"]
        }
    },
    "socket_timeout": 30,
    "retries": 2,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "referer": "https://www.youtube.com/",
    "http_headers": {
        "Accept": "*/*",
        "X-Goog-Api-Format-Version": "2",
        "X-Youtube-Client-Name": "1",
        "X-Youtube-Client-Version": "2.20240111.09.00",
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
                
                # Get the direct media URL (not webpage URL)
                # yt-dlp provides 'url' for direct media stream or 'webpage_url' for video page
                url = info.get("url")
                if not url or "youtube.com" in url or "youtu.be" in url:
                    # If we got a webpage URL, try to get formats
                    formats = info.get("formats", [])
                    if formats:
                        # Get the best audio format
                        for fmt in reversed(formats):
                            if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                                url = fmt.get("url")
                                break
                        if not url and formats:
                            url = formats[-1].get("url")
                
                if not url:
                    raise Exception("No playable URL found")
                    
                title = info.get("title") or "Audio"
                thumb = info.get("thumbnail")
                vid = info.get("id")
                duration_str = _format_duration(info.get("duration"))
                views_str = _human_views(info.get("view_count"))
                logger.info(f"Extracted: {title} (Duration: {duration_str})")
                return url, title, thumb, vid, views_str, duration_str
        except Exception as e:
            logger.warning(f"Primary extraction failed: {e}")
            
            # Fallback 1: Try with different Invidious instances sequentially
            for invidious_url in INVIDIOUS_INSTANCES:
                try:
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
                        
                        url = info.get("url")
                        if not url or "youtube.com" in url or "youtu.be" in url:
                            formats = info.get("formats", [])
                            if formats:
                                for fmt in reversed(formats):
                                    if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                                        url = fmt.get("url")
                                        break
                                if not url and formats:
                                    url = formats[-1].get("url")
                        
                        if not url:
                            continue
                            
                        title = info.get("title") or "Audio"
                        thumb = info.get("thumbnail")
                        vid = info.get("id")
                        duration_str = _format_duration(info.get("duration"))
                        views_str = _human_views(info.get("view_count"))
                        logger.info(f"Invidious fallback successful: {title}")
                        return url, title, thumb, vid, views_str, duration_str
                except Exception as fallback_error:
                    logger.warning(f"Invidious fallback {invidious_url} failed: {fallback_error}")
                    continue
            
            # All methods failed
            logger.error("All extraction methods failed")
            raise Exception(f"YouTube blocked (bot detection). Try again later or use different query.")
    
    return await asyncio.to_thread(_extract)
