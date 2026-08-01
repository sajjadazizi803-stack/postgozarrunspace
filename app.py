from bot import create_bot
import database
import asyncio
from bot import tg_client


def main():

    print("🔄 Connecting Telegram account...")

    asyncio.run(tg_client.start())

    print("✅ Telegram account connected.")

    app = create_bot()

    print("🔮 PostGozar Started...")

    app.run_polling()


if __name__ == "__main__":
    main()
