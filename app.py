from bot import create_bot
import database


def main():

    app = create_bot()

    print("🔮 PostGozar Started...")

    app.run_polling()


if __name__ == "__main__":
    main()
