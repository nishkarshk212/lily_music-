import random
from typing import List
from pyrogram import Client
from .config import STICKER_SET_URL, STICKER_SET_URLS

def _parse_set_name(url: str) -> str:
    if not url:
        return ""
    try:
        name = url.strip().split("/")[-1]
        name = name.split("?")[0]
        return name
    except Exception:
        return url
    
def _parse_set_names() -> List[str]:
    urls = []
    if STICKER_SET_URLS:
        urls = [u.strip() for u in STICKER_SET_URLS.replace("|", ",").split(",") if u.strip()]
    if STICKER_SET_URL and STICKER_SET_URL.strip():
        urls.append(STICKER_SET_URL.strip())
    names = []
    for u in urls:
        n = _parse_set_name(u)
        if n:
            names.append(n)
    return names

class StickerPool:
    def __init__(self) -> None:
        self._names: List[str] = _parse_set_names()
        self._ids: List[str] = []
        self._ids_anim: List[str] = []

    async def _ensure(self, client: Client) -> None:
        if self._ids:
            return
        if not self._names:
            return
        ids: List[str] = []
        ids_anim: List[str] = []
        for name in self._names:
            try:
                st = await client.get_sticker_set(name)
                for s in getattr(st, "stickers", []):
                    fid = getattr(s, "file_id", None)
                    if not fid:
                        continue
                    ids.append(fid)
                    if getattr(s, "is_animated", False):
                        ids_anim.append(fid)
            except Exception:
                continue
        self._ids = ids
        self._ids_anim = ids_anim

    async def random_id(self, client: Client, animated_only: bool = False) -> str:
        await self._ensure(client)
        pool = self._ids_anim if animated_only and self._ids_anim else self._ids
        if not pool:
            return ""
        return random.choice(pool)
