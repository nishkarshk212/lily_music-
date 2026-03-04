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

# List of Piped instances (alternative to Invidious, often more reliable)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://pipedapi.in.projectsegfau.lt",
    "https://pipedapi.yt1.es",
    "https://pipedapi.nosebs.ru",
]

def get_piped_url():
    """Get a random working Piped instance"""
    return random.choice(PIPED_INSTANCES)

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
        import requests
        
        # Strategy 1: Try Piped API first (bypasses YouTube bot detection)
        try:
            logger.info(f"Attempting Piped API for: {query[:50]}")
            piped_url = get_piped_url()
            
            # Search for the query
            search_url = f"{piped_url}/search?q={requests.utils.quote(query)}&filter=music_songs"
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("items"):
                video = data["items"][0]
                video_id = video.get("url", "").replace("/watch?v=", "")
                
                if video_id:
                    # Get stream info
                    stream_url = f"{piped_url}/streams/{video_id}"
                    stream_response = requests.get(stream_url, timeout=10)
                    stream_response.raise_for_status()
                    stream_data = stream_response.json()
                    
                    # Find audio streams
                    audio_streams = [s for s in stream_data.get("audioStreams", []) if s.get("format") == "M4A"]
                    if audio_streams:
                        # Get highest quality M4A stream
                        url = audio_streams[-1].get("url")
                        title = stream_data.get("title", video.get("title", "Unknown"))
                        thumb = stream_data.get("thumbnailUrl", video.get("thumbnail", ""))
                        vid = video_id
                        duration_str = _format_duration(stream_data.get("duration"))
                        views_str = _human_views(stream_data.get("views"))
                        
                        logger.info(f"Piped API successful: {title}")
                        return url, title, thumb, vid, views_str, duration_str
        except Exception as e:
            logger.warning(f"Piped API failed: {e}")
        
        # Strategy 2: Fall back to direct YouTube with yt-dlp
        try:
            logger.info(f"Attempting direct YouTube extraction for: {query[:50]}")
            with YoutubeDL(AUDIO_YDL_OPTS) as ydl:
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
                    raise Exception("No playable URL found")
                    
                title = info.get("title") or "Audio"
                thumb = info.get("thumbnail")
                vid = info.get("id")
                duration_str = _format_duration(info.get("duration"))
                views_str = _human_views(info.get("view_count"))
                logger.info(f"YouTube extracted: {title} (Duration: {duration_str})")
                return url, title, thumb, vid, views_str, duration_str
        except Exception as e:
            logger.error(f"YouTube extraction failed: {e}")
            raise Exception(f"YouTube playback unavailable. The server's network is blocking YouTube. Please use SoundCloud URLs instead.")
    
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
