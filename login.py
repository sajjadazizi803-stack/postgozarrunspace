from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 38174523
api_hash = "07b04824d0e1185a59b919ba672ec679"

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())
