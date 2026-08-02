from telegram import Update
from telegram.ext import ContextTypes
from conversation import State
from database import add_transfer
from listener import add_new_transfer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import jdatetime
from datetime import datetime

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
    context.user_data["source_channel"] = source_channel
    context.user_data["state"] = State.TARGET_CHANNEL

    await update.message.reply_text(f"""✅ کانال مبدا ثبت شد.
📢 {source_channel}

حالا لینک یا یوزرنیم کانال مقصد را ارسال کنید.
مثال: @target_channel""")


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

    telegram_id = update.effective_user.id

    # ذخیره در دیتابیس
    try:

        add_transfer(
            telegram_id,
            source_channel,
            target_channel,
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ خطا در ذخیره‌سازی:\n\n<code>{e}</code>",
            parse_mode="HTML",
        )

        return

    # فعال کردن لیسنر جدید
    try:

        await add_new_transfer(
            telegram_id,
            source_channel,
            target_channel,
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ خطا در فعال‌سازی انتقال:\n\n<code>{e}</code>",
            parse_mode="HTML",
        )

        return

    context.user_data["state"] = State.NONE

    await update.message.reply_text(
        f"""✅ انتقال با موفقیت ثبت و فعال شد.

📥 کانال مبدا: {source_channel}
📤 کانال مقصد: {target_channel}

🚀 از این به بعد هر پست جدیدی که در کانال مبدا منتشر شود، به صورت خودکار در کانال مقصد نیز ارسال خواهد شد."""
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
                "🗑 حذف انتقال",
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
