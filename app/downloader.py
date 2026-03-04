import asyncio
from typing import Optional, Tuple
from yt_dlp import YoutubeDL

AUDIO_YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "skip_download": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extractor_args": {"youtube": {"skip": ["hls", "dash"]}},
    "check_formats": "selected",
    "youtube_include_dash_manifest": False,
    "youtube_include_hls_manifest": False,
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
    return await asyncio.to_thread(_extract)
