from bot import create_bot

import database


def main():

    print("🔮 PostGozar Started...")

    app = create_bot()

    app.run_polling()


if __name__ == "__main__":
    main()
