from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 38174523
api_hash = "07b04824d0e1185a59b919ba672ec679"

client = TelegramClient(StringSession(), api_id, api_hash)

client.start(phone=lambda: input("Phone: "))

print("\n\n========== STRING SESSION ==========\n")
print(client.session.save())
print("\n====================================\n")

client.disconnect()
