from bot import create_bot
import asyncio
from listener import start_all_listeners
import database


def main():

    print("🔮 PostGozar Started...")

    asyncio.run(start_all_listeners())

    app = create_bot()

    app.run_polling()


if __name__ == "__main__":
    main()
