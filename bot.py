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
from telethon import TelegramClient
from telethon.sessions import StringSession

SESSION_STRING = "1BJWap1wBu7t-Bk8MkUr87Izyg0ZY4uro9zk1Rss1-ZbG2BmguQRVK8m2J1HlrH0z7n8yPzKKy3qhGZaf6-I-jRw6ZUqF-CwPlCsAHM7wb5OXNxXr-RKM2kMWj5zrJeKrqlfqRlIwmWpxUVyeegbD57WI0agh3oLYQ9w-4DxHG2w82Gro_Syvt7VhRrMqnZTDjS4Q4R42c_v18uT7O4Q2MzYwRpQX1LWThaxRHbHMEIMXGF6HpwAVsFN9hdQczoIZeUh66HmhhVKzgIavIVheuI6CPZhx2XCxDp2OBCBKOEvwBu7kZmSiKipc2-WMIPAsc9_Gjnx9elXDBu9TicYO8YS3GWLTZUY="

tg_client = TelegramClient(
    StringSession(SESSION_STRING),
    config.API_ID,
    config.API_HASH,
)

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

    if context.user_data.get("state") == State.SOURCE_CHANNEL:
        return await receive_source_channel(update, context)

    if context.user_data.get("state") == State.TARGET_CHANNEL:
        return await receive_target_channel(update, context)


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
        await tg_client.start()

        from listener import start_all_listeners

        await start_all_listeners()

    app.post_init = startup

    return app
