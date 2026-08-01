from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio

# ================
# اطلاعات API خود را اینجا وارد کنید
# ================

API_ID = 38174523
API_HASH = "07b04824d0e1185a59b919ba672ec679"


async def main():
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        await client.start()
        print("\n✅ String Session جدید شما:\n")
        print(client.session.save())
        print("\n⚠️ این مقدار رو کپی کن و توی فایل bot.py جایگزین کن.")


asyncio.run(main())
