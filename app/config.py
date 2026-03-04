import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
USER_SESSION = os.getenv("USER_SESSION", "")
USER_PHONE = os.getenv("PHONE", "")
SUDO_USERS = {int(x) for x in os.getenv("SUDO_USERS", "").split() if x.isdigit()}
LOG_CHAT_ID = int(os.getenv("LOG_CHAT_ID", "0")) if os.getenv("LOG_CHAT_ID") else None
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", os.path.join(os.getcwd(), "downloads"))
FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")
DISABLE_PLAY_ANNOUNCE = os.getenv("DISABLE_PLAY_ANNOUNCE", "0").lower() in ("1", "true", "yes", "on")
PROMO_ENABLED = os.getenv("PROMO_ENABLED", "1").lower() in ("1", "true", "yes", "on")
PROMO_INTERVAL = int(os.getenv("PROMO_INTERVAL", "900"))
PROMO_MESSAGES = os.getenv("PROMO_MESSAGES", "")
PROMO_CHANNEL = os.getenv("PROMO_CHANNEL", "@Lover_society")
SEARCH_STICKER_FILE_ID = os.getenv("SEARCH_STICKER_FILE_ID", "")
DOWNLOAD_STICKER_FILE_ID = os.getenv("DOWNLOAD_STICKER_FILE_ID", "")
JOIN_STICKER_FILE_ID = os.getenv("JOIN_STICKER_FILE_ID", "")
PLAY_STICKER_FILE_ID = os.getenv("PLAY_STICKER_FILE_ID", "")
ERROR_STICKER_FILE_ID = os.getenv("ERROR_STICKER_FILE_ID", "")
STICKER_SET_URL = os.getenv("STICKER_SET_URL", "https://t.me/addstickers/BurntxMini_by_stickersthiefbot")
STICKER_RANDOM_ENABLED = os.getenv("STICKER_RANDOM_ENABLED", "1").lower() in ("1", "true", "yes", "on")
STICKER_SET_URLS = os.getenv("STICKER_SET_URLS", "")
SEARCH_STAGE_LINK = os.getenv("SEARCH_STAGE_LINK", "")

if not os.path.isdir(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
