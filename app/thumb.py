import os
import asyncio
import requests
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def _ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def _load_font(name: str, size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        try:
            return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
        except Exception:
            return ImageFont.load_default()

def _download(url: str, path: str) -> None:
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)

async def generate_thumbnail(video_id: Optional[str], title: str, views: str, duration: str, bot_username: str) -> str:
    out_dir = os.path.join(os.getcwd(), "downloads", "thumbs")
    _ensure_dir(out_dir)
    
    # Ensure video_id is never None
    safe_video_id = video_id or "default_thumb"
    
    tmp_path = os.path.join(out_dir, f"{safe_video_id}.jpg")
    url = f"https://img.youtube.com/vi/{safe_video_id}/hqdefault.jpg"
    if url:
        await asyncio.to_thread(_download, url, tmp_path)
    else:
        tmp_path = os.path.join(out_dir, "blank.jpg")
        img = Image.new("RGB", (1280, 720), color=(30, 30, 30))
        img.save(tmp_path)
    bg = Image.open(tmp_path).resize((1280, 720)).filter(ImageFilter.GaussianBlur(25))
    fg = Image.open(tmp_path).resize((640, 360))
    bg.paste(fg, (320, 180))
    draw = ImageDraw.Draw(bg)
    font_big = _load_font("arial.ttf", 60)
    font_small = _load_font("arial.ttf", 40)
    draw.text((60, 560), title[:60], font=font_big, fill="white")
    info = f"YouTube • {views} | Time • {duration} | Player • @{bot_username}"
    draw.text((60, 640), info, font=font_small, fill="#ff2e88")
    output = os.path.join(out_dir, f"{video_id or 'thumb'}_final.png")
    bg.save(output)
    return output
