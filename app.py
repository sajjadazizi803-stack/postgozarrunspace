from bot import create_bot
from telegram_client import tg_client
from listener import start_all_listeners
import asyncio


async def startup(app):
    await tg_client.connect()
    await start_all_listeners()


def main():
    app = create_bot()
    app.post_init = startup
    app.run_polling()


if __name__ == "__main__":
    main()
