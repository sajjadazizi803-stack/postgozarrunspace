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

from handlers.connect_account import (
    delete_transfer_callback,
    toggle_transfer_callback,
    back_to_registered_channels,
)

import config
from telegram_client import tg_client
from handlers.connect_account import registered_channels
from handlers.connect_account import transfer_info

# =========================
# START
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = ReplyKeyboardMarkup(
        [
            ["📢 افزودن کانال"],
            ["📋 کانال‌های ثبت شده"],
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

    # اگر داخل یکی از مراحل گفتگو هستیم، دکمه‌های اصلی کار نکنند
    if context.user_data.get("state", State.NONE) != State.NONE:
        return

    text = update.message.text

    if text == "📢 افزودن کانال":
        await connect_account(update, context)
        return

    if text == "📋 کانال‌های ثبت شده":
        await registered_channels(update, context)
        return


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

    from telegram.ext import CallbackQueryHandler

    app.add_handler(
        CallbackQueryHandler(
            transfer_info,
            pattern=r"^transfer_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_transfer_callback,
            pattern=r"^delete_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            toggle_transfer_callback,
            pattern=r"^toggle_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            back_to_registered_channels,
            pattern=r"^registered_channels$",
        )
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(CallbackQueryHandler(buttons))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
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

        try:
            await tg_client.start()
        except Exception:
            pass

        try:
            from listener import start_all_listeners

            await start_all_listeners()

        except Exception:
            pass

    app.post_init = startup

    return app
