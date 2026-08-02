from telegram import Update
from telegram.ext import ContextTypes
from conversation import State
from database import add_transfer
from listener import add_new_transfer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import jdatetime
from datetime import datetime
from telegram_client import tg_client
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import UserAlreadyParticipantError
from telegram import ChatMemberAdministrator
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError

from database import (
    delete_transfer,
    set_transfer_enabled,
    get_user_transfers,
    get_remove_last_lines,
    set_append_last_lines,
    get_append_last_lines,
)

# =========================
# connect account
# =========================


async def connect_account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            """📢 لطفاً لینک یا یوزرنیم کانال مبدا را ارسال کنید.
مثال: @source_channel"""
        )
    else:
        await update.message.reply_text(
            """📢 لطفاً لینک یا یوزرنیم کانال مبدا را ارسال کنید.
مثال: @source_channel"""
        )

    context.user_data["state"] = State.SOURCE_CHANNEL


# =========================
# receive source channel
# =========================


async def receive_source_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("state") != State.SOURCE_CHANNEL:
        return

    source_channel = update.message.text.strip()

    try:

        try:
            await tg_client(JoinChannelRequest(source_channel))
        except UserAlreadyParticipantError:
            pass

    except Exception:

        await update.message.reply_text("❌ عضویت در کانال مبدا انجام نشد.")
        return

    context.user_data["source_channel"] = source_channel
    context.user_data["state"] = State.TARGET_CHANNEL

    await update.message.reply_text(f"""✅ اکانت عضو کانال مبدا شد.

📥 {source_channel}

حالا آیدی کانال مقصد را ارسال کنید.""")


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

        await update.message.reply_text("❌ کانال مبدا پیدا نشد.")

        return

    try:

        await tg_client(JoinChannelRequest(target_channel))

    except:
        pass

    context.user_data["pending_source"] = source_channel
    context.user_data["pending_target"] = target_channel

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ انجام شد",
                callback_data="finish_transfer",
            )
        ]
    ]

    context.user_data["state"] = State.NONE

    await update.message.reply_text(
        f"""✅ اکانت عضو کانال مقصد شد.

📥 مبدا:
{source_channel}

📤 مقصد:
{target_channel}

اکنون:

1- ربات را ادمین کانال مقصد کنید.

2- اکانت را نیز ادمین کنید.

سپس روی دکمه زیر بزنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------------------- registered channels --------------------


async def registered_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    transfers = get_user_transfers(user_id)

    if not transfers:
        await update.message.reply_text("❌ هنوز هیچ کانالی ثبت نکرده‌اید.")
        return

    keyboard = []

    for transfer in transfers:

        transfer_id = transfer[0]
        source = transfer[1]
        target = transfer[2]

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{source} ➜ {target}", callback_data=f"transfer_{transfer_id}"
                )
            ]
        )

    await update.message.reply_text(
        """<b>📋 کانال‌های ثبت‌شده شما</b>

🎯 تمام اتصال‌های فعال شما در این بخش نمایش داده می‌شوند.

👇 برای مشاهده اطلاعات هر اتصال، کافی است روی دکمه <b>کانال مبدا ➜ مقصد</b> موردنظر بزنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# -------------------- transfer info --------------------


async def transfer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[1])

    transfers = get_user_transfers(query.from_user.id)

    transfer = None

    for item in transfers:
        if item[0] == transfer_id:
            transfer = item
            break

    if transfer is None:
        await query.edit_message_text("❌ انتقال پیدا نشد.")
        return

    source = transfer[1]
    target = transfer[2]
    enabled = transfer[3]
    sent_count = transfer[4]
    last_send = transfer[5]

    # تبدیل تاریخ میلادی به شمسی
    if last_send:
        try:
            dt = datetime.strptime(str(last_send), "%Y-%m-%d %H:%M:%S")
            jalali_date = jdatetime.datetime.fromgregorian(datetime=dt)

            last_send = jalali_date.strftime("%Y/%m/%d • %H:%M")

        except Exception:
            pass

    status = "🟢 فعال" if enabled else "🔴 متوقف"

    keyboard = [
        [
            InlineKeyboardButton(
                "⏸ توقف" if enabled else "▶️ فعال",
                callback_data=f"toggle_{transfer_id}",
            ),
            InlineKeyboardButton(
                "🗑 حذف",
                callback_data=f"delete_{transfer_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data=f"settings_{transfer_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="registered_channels",
            )
        ],
    ]

    await query.edit_message_text(
        f"""📡 اطلاعات انتقال

📥 مبدا: {source}
📤 مقصد: {target}

📨 تعداد پیام: {sent_count}
🕒 آخرین انتقال: {last_send if last_send else "هنوز انتقالی انجام نشده"}

📊 وضعیت: {status}
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------------------- back to registered channels --------------------


async def back_to_registered_channels(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    transfers = get_user_transfers(query.from_user.id)

    keyboard = []

    for transfer in transfers:

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{transfer[1]} ➜ {transfer[2]}",
                    callback_data=f"transfer_{transfer[0]}",
                )
            ]
        )
    # -
    await query.edit_message_text(
        """<b>📋 کانال‌های ثبت‌شده شما</b>

🎯 تمام اتصال‌های فعال شما در این بخش نمایش داده می‌شوند.

👇 برای مشاهده اطلاعات هر اتصال، کافی است روی دکمه <b>کانال مبدا ➜ مقصد</b> موردنظر بزنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# -------------------- bdelete transfer callback --------------------


async def delete_transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[1])

    delete_transfer(transfer_id)

    await back_to_registered_channels(update, context)


# -------------------- toggle transfer callback --------------------


async def toggle_transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[1])

    transfers = get_user_transfers(query.from_user.id)

    for transfer in transfers:

        if transfer[0] == transfer_id:

            enabled = transfer[3]

            set_transfer_enabled(
                transfer_id,
                0 if enabled else 1,
            )

            break

    # دوباره اطلاعات جدید انتقال را بگیر
    transfers = get_user_transfers(query.from_user.id)

    transfer = None

    for item in transfers:
        if item[0] == transfer_id:
            transfer = item
            break

    if transfer is None:
        await query.edit_message_text("❌ انتقال پیدا نشد.")
        return

    source = transfer[1]
    target = transfer[2]
    enabled = transfer[3]
    sent_count = transfer[4]
    last_send = transfer[5]

    if last_send:
        try:
            dt = datetime.strptime(str(last_send), "%Y-%m-%d %H:%M:%S")
            jalali_date = jdatetime.datetime.fromgregorian(datetime=dt)
            last_send = jalali_date.strftime("%Y/%m/%d • %H:%M")
        except Exception:
            pass

    status = "🟢 فعال" if enabled else "🔴 متوقف"

    keyboard = [
        [
            InlineKeyboardButton(
                "⏸ توقف" if enabled else "▶️ فعال",
                callback_data=f"toggle_{transfer_id}",
            ),
            InlineKeyboardButton(
                "🗑 حذف",
                callback_data=f"delete_{transfer_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data=f"settings_{transfer_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="registered_channels",
            )
        ],
    ]

    await query.edit_message_text(
        f"""📡 اطلاعات انتقال

📥 مبدا: {source}
📤 مقصد: {target}

📨 تعداد پیام: {sent_count}
🕒 آخرین انتقال: {last_send if last_send else "هنوز انتقالی انجام نشده"}

📊 وضعیت: {status}
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------------------- transfer settings --------------------


async def transfer_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[1])

    keyboard = [
        [
            InlineKeyboardButton(
                "✂️ حذف خطوط آخر",
                callback_data=f"remove_lines_{transfer_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "➕ افزودن خطوط آخر",
                callback_data=f"append_lines_{transfer_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data=f"transfer_{transfer_id}",
            )
        ],
    ]

    await query.edit_message_text(
        """⚙️ تنظیمات انتقال

تنظیماتی که می‌خواهید ربات روی هر پست اعمال کند را انتخاب کنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------------------- remove lines setting --------------------


async def remove_lines_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    context.user_data["remove_lines_transfer_id"] = transfer_id

    context.user_data["state"] = State.REMOVE_LAST_LINES

    await query.edit_message_text("""✂️ حذف خطوط آخر

چند خط آخر پست حذف شود؟

مثال:
8""")


# -------------------- append lines setting --------------------


async def append_lines_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    context.user_data["append_lines_transfer_id"] = transfer_id

    context.user_data["state"] = State.APPEND_LAST_LINES

    await query.edit_message_text("""➕ افزودن خطوط آخر

متنی که می‌خواهید به آخر پست اضافه شود را ارسال کنید.""")


# -------------------- finish transfer --------------------


async def finish_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    source_channel = context.user_data.get("pending_source")
    target_channel = context.user_data.get("pending_target")

    if not source_channel or not target_channel:

        await query.edit_message_text("❌ اطلاعات انتقال پیدا نشد.")
        return

    # ----------------------------------
    # بررسی عضویت اکانت در مبدا
    # ----------------------------------

    try:

        await tg_client(
            GetParticipantRequest(
                source_channel,
                "me",
            )
        )

    except UserNotParticipantError:

        await query.edit_message_text("❌ اکانت داخل کانال مبدا عضو نیست.")

        return

    except Exception:
        pass

    # ----------------------------------
    # بررسی عضویت اکانت در مقصد
    # ----------------------------------

    try:

        await tg_client(
            GetParticipantRequest(
                target_channel,
                "me",
            )
        )

    except UserNotParticipantError:

        await query.edit_message_text("❌ اکانت داخل کانال مقصد عضو نیست.")

        return

    except Exception:
        pass

    # ----------------------------------
    # بررسی وجود ربات در مقصد
    # ----------------------------------

    try:

        bot_member = await context.bot.get_chat_member(
            target_channel,
            context.bot.id,
        )

    except Exception:

        await query.edit_message_text(
            "❌ ربات داخل کانال مقصد نیست.\n\n"
            "ابتدا ربات را به کانال اضافه و ادمین کنید."
        )

        return

    # ----------------------------------
    # بررسی ادمین بودن ربات
    # ----------------------------------

    if bot_member.status not in (
        "administrator",
        "creator",
    ):

        await query.edit_message_text(
            "❌ ربات هنوز ادمین کانال مقصد نیست.\n\n"
            "ابتدا ربات را ادمین کنید سپس دوباره روی «✅ انجام شد» بزنید."
        )

        return

    # ----------------------------------
    # ثبت انتقال
    # ----------------------------------

    add_transfer(
        query.from_user.id,
        source_channel,
        target_channel,
    )

    context.user_data.pop("pending_source", None)
    context.user_data.pop("pending_target", None)

    await query.edit_message_text(f"""✅ انتقال با موفقیت ثبت شد.

📥 مبدا: {source_channel}
📤 مقصد: {target_channel}

🚀 انتقال خودکار از این لحظه فعال شد.""")
