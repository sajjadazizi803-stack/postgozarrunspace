from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)
from database import (
    add_support_message,
    get_support_user,
)
from config import ADMIN_ID
from conversation import State

support_messages = {}


# ------------------- contact support callback --------------------


async def contact_support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["state"] = State.SUPPORT

    await update.message.reply_text(
        "💬 پیامت رو بفرست.\n\nمتن، عکس، فیلم، فایل، ویس و... هم میتونی ارسال کنی."
    )


# ------------------- forward to admin --------------------


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    message = update.effective_message

    header = (
        f"📩 پیام جدید پشتیبانی\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 آیدی: {user.id}\n"
        f"📎 یوزرنیم: @{user.username if user.username else '-'}"
    )

    if message.text:

        admin_msg = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"{header}\n\n{message.text}",
            parse_mode="Markdown",
        )

    else:

        admin_msg = await message.copy(
            chat_id=ADMIN_ID,
            caption=(f"{header}\n\n{message.caption}" if message.caption else header),
            parse_mode="Markdown",
        )

    add_support_message(
        admin_msg.message_id,
        user.id,
    )

    await message.reply_text("✅ پیام شما برای پشتیبانی ارسال شد.")

    context.user_data["state"] = State.NONE

    return ConversationHandler.END


# ------------------- admin reply --------------------


async def admin_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    message = update.effective_message

    if not message.reply_to_message:
        return

    user_id = get_support_user(message.reply_to_message.message_id)

    if not user_id:
        return

    if message.text:

        await context.bot.send_message(
            chat_id=user_id,
            text=f"💬 پاسخ پشتیبانی:\n\n{message.text}",
        )

    else:

        await message.copy(
            chat_id=user_id,
            caption=(
                f"💬 پاسخ پشتیبانی\n\n{message.caption}"
                if message.caption
                else "💬 پاسخ پشتیبانی"
            ),
        )

    await message.reply_text("✅ پاسخ برای کاربر ارسال شد.")
