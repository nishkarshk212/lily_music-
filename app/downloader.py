import asyncio
from typing import Optional, Tuple
from yt_dlp import YoutubeDL
import logging
import random
import os
import uuid

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# List of Invidious instances as fallback for YouTube
INVIDIOUS_INSTANCES = [
    "https://invidious.io.lol",
    "https://inv.tux.pizza", 
    "https://yt.artemislena.eu",
    "https://invidious.tiekoetter.com",
    "https://inv.nadeko.net",
    "https://yewtu.be",
    "https://vid.puffyan.us",
    "https://invidious.fdn.fr",
    "https://youtube.0x58.me",
    "https://yt.drgnz.org",
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
    # Use TV embedded client (most reliable for avoiding bot detection)
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "referer": "https://www.youtube.com/",
    "prefer_free_formats": False,
    "extractor_retries": 3,
    "http_headers": {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Goog-Api-Format-Version": "2",
        "Origin": "https://www.youtube.com",
    },
    # Try to bypass age restrictions and bot detection
    "bypass": ["age_gate", "consent"],
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
            "player_client": "web_safari",  # Safari web client - more reliable
            "player_skip": ["webpage"]
        }
    },
    "socket_timeout": 30,
    "retries": 2,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "referer": "https://www.youtube.com/",
    "http_headers": {
        "Accept": "*/*",
        "X-Goog-Api-Format-Version": "2",
        "X-Youtube-Client-Name": "1",
        "X-Youtube-Client-Version": "2.20240111.09.00",
        "Origin": "https://www.youtube.com",
    },
    "bypass": ["age_gate", "consent"],
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
        # Try SoundCloud first (more reliable than YouTube)
        try:
            logger.info(f"Attempting SoundCloud extraction for: {query}")
            sc_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "skip_download": True,
                "no_warnings": True,
            }
            with YoutubeDL(sc_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                
                url = info.get("url")
                if url and ("soundcloud.com" in url or "sndcdn.com" in url):
                    title = info.get("title") or "Audio"
                    thumb = info.get("thumbnail")
                    vid = info.get("id", "sc_" + str(hash(title)))
                    duration_str = _format_duration(info.get("duration"))
                    views_str = _human_views(info.get("playback_count"))
                    logger.info(f"SoundCloud extracted: {title}")
                    return url, title, thumb, vid, views_str, duration_str
        except Exception as e:
            logger.info(f"SoundCloud extraction failed or not SoundCloud URL: {e}")
        
        # Try YouTube as secondary
        try:
            logger.info(f"Attempting YouTube extraction for: {query}")
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
                logger.info(f"YouTube extracted: {title} (Duration: {duration_str})")
                return url, title, thumb, vid, views_str, duration_str
        except Exception as e:
            logger.warning(f"YouTube primary extraction failed: {e}")
            
            # Fallback 1: Try with different Invidious instances sequentially
            import time
            for i, invidious_url in enumerate(INVIDIOUS_INSTANCES):
                try:
                    logger.info(f"Trying Invidious fallback #{i+1}: {invidious_url}")
                    
                    opts = AUDIO_YDL_OPTS_FALLBACK.copy()
                    opts["extractor_args"] = {
                        "youtube": {
                            "skip": ["hls", "dash"],
                            "player_client": "tv_embedded"
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
                    # Wait a bit before trying next instance
                    if i < len(INVIDIOUS_INSTANCES) - 1:
                        time.sleep(0.5)
                    continue
            
            # Fallback 2: Try with web embedded client (last resort)
            try:
                logger.info("Trying web embedded client fallback...")
                opts = {
                    "format": "bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                    "skip_download": True,
                    "no_warnings": True,
                    "extractor_args": {
                        "youtube": {
                            "player_client": "web_embedded",
                            "player_skip": ["webpage"]
                        }
                    },
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "http_headers": {
                        "Accept": "*/*",
                        "Origin": "https://www.youtube.com",
                        "Referer": "https://www.youtube.com",
                    }
                }
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                    
                    url = info.get("url")
                    if not url:
                        formats = info.get("formats", [])
                        if formats:
                            url = formats[-1].get("url")
                    
                    if url:
                        title = info.get("title") or "Audio"
                        thumb = info.get("thumbnail")
                        vid = info.get("id")
                        duration_str = _format_duration(info.get("duration"))
                        views_str = _human_views(info.get("view_count"))
                        logger.info(f"Web embedded fallback successful: {title}")
                        return url, title, thumb, vid, views_str, duration_str
            except Exception as e2:
                logger.warning(f"Web embedded fallback failed: {e2}")
            
            # All methods failed
            logger.error("All extraction methods failed")
            raise Exception(f"YouTube blocked (bot detection). Try again later or use different query.")
    
    return await asyncio.to_thread(_extract)


async def download_audio_file(url: str) -> Tuple[str, dict]:
    """
    Download audio file locally with progress tracking.
    
    Args:
        url: YouTube URL or search query
        
    Returns:
        Tuple of (file_path, info_dict)
    """
    unique_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.%(ext)s")
    
    def progress_hook(d):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A")
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")
            logger.info(f"Downloading: {percent} | Speed: {speed} | ETA: {eta}")
            # Note: Can't call async functions here directly
            # Progress callback will be handled by logging
        elif d["status"] == "finished":
            logger.info("Download finished, processing...")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "progress_hooks": [progress_hook],
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }
    
    def _download():
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            # Convert to mp3
            file_path = file_path.rsplit(".", 1)[0] + ".mp3"
            return file_path, info
    
    return await asyncio.to_thread(_download)


def cleanup_file(file_path: str) -> bool:
    """Remove downloaded file if it exists."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
    return False
