#!/bin/bash

# Test playback on server
echo "Testing playback functionality on server..."
echo ""

ssh root@140.245.240.202 << 'ENDSSH'
cd /root/lily_music-
source venv/bin/activate

# Create a test script
cat > /tmp/test_playback.py << 'PYEOF'
import asyncio
import os
import sys

# Add the project to path
sys.path.insert(0, '/root/lily_music-')

from yt_dlp import YoutubeDL

async def test_extraction():
    """Test if we can extract audio URL from YouTube"""
    print("Testing YouTube extraction...")
    
    opts = {
        "format": "bestaudio[ext=webm]/bestaudio/best",
        "noplaylist": True,
        "quiet": False,  # Show output for debugging
        "skip_download": True,
        "no_warnings": False,
        "default_search": "ytsearch",
        "extractor_args": {
            "youtube": {
                "skip": ["hls", "dash"],
                "player_client": "ios",
                "player_skip": ["webpage"]
            }
        },
        "socket_timeout": 30,
        "retries": 3,
    }
    
    try:
        query = "never gonna give you up"
        print(f"Searching for: {query}")
        
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            
            if "entries" in info:
                info = info["entries"][0]
            
            url = info.get("url")
            title = info.get("title")
            duration = info.get("duration")
            
            print(f"\n✅ SUCCESS!")
            print(f"Title: {title}")
            print(f"Duration: {duration}s")
            print(f"URL: {url[:100]}...")
            return True
            
    except Exception as e:
        print(f"\n❌ FAILED: {e.__class__.__name__}: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_extraction())
    sys.exit(0 if result else 1)
PYEOF

python /tmp/test_playback.py

# Clean up
rm -f /tmp/test_playback.py

ENDSSH
