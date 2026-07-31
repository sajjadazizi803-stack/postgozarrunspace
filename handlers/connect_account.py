from telegram import Update
from telegram.ext import ContextTypes
from telethon import TelegramClient
import config
import os

# =========================
# connect account
# =========================


async def connect_account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["waiting_phone"] = True

    await query.edit_message_text("""📱 اتصال اکانت تلگرام

لطفاً شماره تلفن اکانت تلگرام خود را ارسال کنید.

نمونه:

+989121234567

⚠️ شماره را همراه با کد کشور ارسال کنید.""")


# =========================
# receive phone
# =========================


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_phone"):
        return

    phone = update.message.text.strip()

    context.user_data["waiting_phone"] = False
    context.user_data["phone"] = phone

    session_name = os.path.join(
        config.SESSION_FOLDER,
        str(update.effective_user.id),
    )

    client = TelegramClient(
        session_name,
        config.API_ID,
        config.API_HASH,
        connection_retries=1,
        timeout=20,
    )

    try:
        await client.connect()

        await client.send_code_request(phone)

        context.user_data["client"] = client
        context.user_data["waiting_code"] = True

        await update.message.reply_text(
            f"""📨 کد تأیید به شماره

<code>{phone}</code>

ارسال شد.

لطفاً کد ۵ رقمی دریافتی از تلگرام را ارسال کنید.

مثال:

<code>12345</code>""",
            parse_mode="HTML",
        )

    except Exception as e:

        await client.disconnect()

        await update.message.reply_text(
            f"""❌ خطا در ارسال کد تأیید.

<code>{e}</code>""",
            parse_mode="HTML",
        )
