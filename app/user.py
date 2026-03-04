from pyrogram import Client
from typing import Optional
import os

def create_user(session: str, api_id: int, api_hash: str) -> Client:
    workdir = os.path.join(os.getcwd(), "sessions", "user")
    os.makedirs(workdir, exist_ok=True)
    return Client("user", api_id=api_id, api_hash=api_hash, session_string=session, workdir=workdir)
