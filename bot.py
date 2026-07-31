from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
    receive_phone,
)

import config

# =========================
# START
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ اتصال اکانت",
                    callback_data="connect_account",
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 لیست انتقال‌ها",
                    callback_data="transfer_list",
                )
            ],
            [
                InlineKeyboardButton(
                    "➕ ساخت انتقال جدید",
                    callback_data="new_transfer",
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙ تنظیمات",
                    callback_data="settings",
                )
            ],
        ]
    )

    await update.message.reply_text(
        """🚀 به ربات PostGozar خوش آمدید.

با این ربات می‌توانید:

• اکانت تلگرام خود را متصل کنید.
• یک کانال مبدا انتخاب کنید.
• یک کانال مقصد انتخاب کنید.
• پست‌های کانال مبدا را به صورت خودکار در مقصد منتشر کنید.

یکی از گزینه‌های زیر را انتخاب کنید.""",
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

    elif query.data == "transfer_list":

        await query.edit_message_text("📋 هنوز انتقالی ثبت نشده است.")

    elif query.data == "new_transfer":

        await query.edit_message_text("➕ ساخت انتقال جدید\n\n(به زودی)")

    elif query.data == "settings":

        await query.edit_message_text("⚙ تنظیمات\n\n(به زودی)")


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
            filters.TEXT & ~filters.COMMAND,
            receive_phone,
        )
    )

    return app
