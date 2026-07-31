from telethon.sync import TelegramClient

api_id = 38174523
api_hash = "07b04824d0e1185a59b919ba672ec679"

client = TelegramClient("my_account", api_id, api_hash)

client.start(phone=lambda: input("Phone: "))

print("LOGIN SUCCESS")

client.disconnect()
