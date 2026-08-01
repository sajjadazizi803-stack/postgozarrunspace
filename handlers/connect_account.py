from telegram import Update
from telegram.ext import ContextTypes
from conversation import State
from database import add_transfer

# =========================
# connect account
# =========================


async def connect_account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:
        await update.callback_query.answer()

        await update.callback_query.edit_message_text(
            """📢 لطفاً لینک یا یوزرنیم کانال مبدا را ارسال کنید.

مثال:
@source_channel"""
        )
    else:
        await update.message.reply_text(
            """📢 لطفاً لینک یا یوزرنیم کانال مبدا را ارسال کنید.

مثال:
@source_channel"""
        )

    context.user_data["state"] = State.SOURCE_CHANNEL


# =========================
# receive source channel
# =========================


async def receive_source_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("state") != State.SOURCE_CHANNEL:
        return

    source_channel = update.message.text.strip()

    context.user_data["source_channel"] = source_channel

    context.user_data["state"] = State.TARGET_CHANNEL

    await update.message.reply_text(f"""✅ کانال مبدا ثبت شد.

📢 {source_channel}

حالا لینک یا یوزرنیم کانال مقصد را ارسال کنید.

مثال:
@target_channel""")


# =========================
# receive target channel
# =========================


async def receive_target_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("state") != State.TARGET_CHANNEL:
        return

    target_channel = update.message.text.strip()

    source_channel = context.user_data.get("source_channel")

    if not source_channel:
        context.user_data["state"] = State.NONE

        await update.message.reply_text(
            "❌ خطا: کانال مبدا پیدا نشد.\n\nدوباره از ابتدا شروع کنید."
        )
        return

    # ذخیره در دیتابیس
    add_transfer(
        update.effective_user.id,
        source_channel,
        target_channel,
    )

    # ذخیره موقت در حافظه (در صورت نیاز)
    context.user_data["target_channel"] = target_channel

    # پایان گفتگو
    context.user_data["state"] = State.NONE

    await update.message.reply_text(f"""✅ انتقال با موفقیت ثبت شد.

📥 کانال مبدا:
{source_channel}

📤 کانال مقصد:
{target_channel}

🚀 از این به بعد هر پست جدیدی که در کانال مبدا منتشر شود،
به صورت خودکار در کانال مقصد نیز ارسال خواهد شد.""")
