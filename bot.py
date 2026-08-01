from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from handlers.connect_account import (
    connect_account,
    receive_source_channel,
    receive_target_channel,
)

import config
from telegram_client import tg_client

# =========================
# START
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = ReplyKeyboardMarkup(
        [
            ["📢 افزودن کانال"],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        """🚀 به ربات PostGozar خوش آمدید.

با این ربات می‌توانید:

• یک کانال مبدا انتخاب کنید.
• یک کانال مقصد انتخاب کنید.
• پست‌های کانال مبدا را به صورت خودکار در مقصد منتشر کنید.""",
        reply_markup=keyboard,
    )


# =========================
# BUTTONS
# =========================


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "connect_account":
        await connect_account(update, context)


# =========================
# text buttons
# =========================


from conversation import State


async def text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # اگر داخل یک گفتگو هستیم، هیچ کاری نکن
    if context.user_data.get("state", State.NONE) != State.NONE:
        return

    if update.message.text == "📢 افزودن کانال":
        await connect_account(update, context)


# =========================
# conversation router
# =========================

from handlers.connect_account import (
    connect_account,
    receive_source_channel,
    receive_target_channel,
)


async def conversation_router(update, context):

    user_data = context.user_data or {}

    state = user_data.get("state", State.NONE)

    if state == State.SOURCE_CHANNEL:
        return await receive_source_channel(update, context)

    if state == State.TARGET_CHANNEL:
        return await receive_target_channel(update, context)

    return


# =========================
# CREATE BOT
# =========================


def create_bot():

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(CallbackQueryHandler(buttons))

    app.add_handler(
        MessageHandler(
            filters.Regex("^📢 افزودن کانال$"),
            text_buttons,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            conversation_router,
        )
    )

    # تلگرام کلاینت
    app.bot_data["tg_client"] = tg_client

    # اجرا هنگام بالا آمدن ربات
    async def startup(app):

        print("========== STARTUP ==========")

        try:

            await tg_client.start()
            print("✅ tg_client started")
        except Exception as e:
            print("❌ tg_client start error:", e)

        try:
            from listener import start_all_listeners

            print("➡️ calling start_all_listeners()")

            await start_all_listeners()

            print("✅ start_all_listeners finished")

        except Exception as e:
            print("❌ start_all_listeners error:", e)

    app.post_init = startup

    return app
