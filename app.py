from bot import create_bot
from telegram_client import tg_client
from handlers.connect_account import finish_transfer
import asyncio


async def telethon_worker():

    try:
        if not tg_client.is_connected():
            await tg_client.connect()

        from listener import start_all_listeners

        await start_all_listeners()

        await tg_client.run_until_disconnected()

    except Exception as e:
        pass


async def startup(app):

    asyncio.create_task(telethon_worker())

    print("🚀 PostGozar Bot Started Successfully.")


def main():

    app = create_bot()

    app.post_init = startup

    app.run_polling()


if __name__ == "__main__":
    main()
