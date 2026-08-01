from bot import create_bot
from telegram_client import tg_client
from listener import start_all_listeners

import asyncio


async def telethon_worker():

    if not tg_client.is_connected():
        await tg_client.connect()

    await start_all_listeners()

    await tg_client.run_until_disconnected()


async def startup(app):

    asyncio.create_task(telethon_worker())

    print("🚀 PostGozar Bot Started Successfully.")


def main():

    app = create_bot()

    app.post_init = startup

    app.run_polling()


if __name__ == "__main__":
    main()
