import os

from telethon import TelegramClient
from telethon.sessions import StringSession

import config

SESSION_STRING = os.getenv("BOT_SESSION_STRING")

if not SESSION_STRING:
    raise RuntimeError("❌ BOT_SESSION_STRING در Railway تنظیم نشده است.")


tg_client = TelegramClient(
    StringSession(SESSION_STRING),
    config.API_ID,
    config.API_HASH,
)
