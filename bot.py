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
    transfer_settings,
    remove_lines_setting,
)

import config
from telegram_client import tg_client
from handlers.connect_account import registered_channels
from handlers.connect_account import transfer_info
from database import set_remove_last_lines

# ---------------------- clear waiting state --------------------


def clear_waiting_state(context):
    context.user_data["state"] = State.NONE


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

    if update.effective_user is None:
        return

    if update.message is None:
        return

    user_data = context.user_data

    if user_data is None:
        return

    text = update.message.text

    # دکمه‌هایی که باعث لغو حالت انتظار می‌شوند
    MAIN_BUTTONS = [
        "📢 افزودن کانال",
        "📋 کانال‌های ثبت شده",
    ]

    if text in MAIN_BUTTONS:
        clear_waiting_state(context)

    state = user_data.get("state", State.NONE)

    # =========================
    # دریافت کانال مبدا
    # =========================
    if state == State.SOURCE_CHANNEL:
        await receive_source_channel(update, context)
        return

    # =========================
    # حذف خطوط آخر
    # =========================
    if state == State.REMOVE_LAST_LINES:

        try:
            count = int(update.message.text.strip())

        except:

            await update.message.reply_text("❌ لطفاً فقط عدد ارسال کنید.\nمثال: 8")

            return

        transfer_id = context.user_data.get("remove_lines_transfer_id")

        if transfer_id:

            set_remove_last_lines(
                transfer_id,
                count,
            )

        context.user_data["state"] = State.NONE

        await update.message.reply_text(
            f"✅ تنظیم شد.\n" f"از این به بعد {count} خط آخر پست‌ها حذف می‌شود."
        )

        return

    # =========================
    # دریافت کانال مقصد
    # =========================
    if state == State.TARGET_CHANNEL:
        await receive_target_channel(update, context)
        return

    # =========================
    # دکمه‌های اصلی
    # =========================
    if text == "📢 افزودن کانال":

        await connect_account(
            update,
            context,
        )

        return

    if text == "📋 کانال‌های ثبت شده":

        await registered_channels(
            update,
            context,
        )

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

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_buttons,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            transfer_settings,
            pattern=r"^settings_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            remove_lines_setting,
            pattern=r"^remove_lines_\d+$",
        )
    )

    app.add_handler(CallbackQueryHandler(buttons))
    app.bot_data["tg_client"] = tg_client

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
