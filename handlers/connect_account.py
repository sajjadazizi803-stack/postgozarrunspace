from telegram import Update
from telegram.ext import ContextTypes
from conversation import State
from database import add_transfer
from listener import (
    add_new_transfer,
    stop_transfer_listener,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import jdatetime
from datetime import datetime
from telegram_client import tg_client
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import UserAlreadyParticipantError
from telegram import ChatMemberAdministrator
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
from telethon.tl import functions
from database import update_transfer_target

from database import (
    delete_transfer,
    set_transfer_enabled,
    get_user_transfers,
    get_remove_last_lines,
    set_append_last_lines,
    get_append_last_lines,
    update_transfer_source,
    update_transfer_target,
    get_transfer_by_id,
)

from telethon.tl.types import (
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
)

change_target_states = {}
# =========================
# connect account
# =========================


async def connect_account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    # ==========================================
    # بررسی اینکه کاربر قبلاً انتقال دارد یا نه
    # ==========================================

    transfers = get_user_transfers(user_id)

    if transfers:

        text = (
            "⚠️ <b>شما قبلاً یک انتقال ثبت کرده‌اید.</b>\n\n"
            "برای تغییر کانال مبدا یا مقصد، "
            "به بخش «📋 انتقال‌های ثبت شده» بروید "
            "و از همان‌جا کانال موردنظر را تغییر دهید."
        )

        if update.callback_query:

            await update.callback_query.answer()

            await update.callback_query.edit_message_text(
                text,
                parse_mode="HTML",
            )

        else:

            await update.message.reply_text(
                text,
                parse_mode="HTML",
            )

        context.user_data["state"] = State.NONE

        return

    # ==========================================
    # شروع ثبت انتقال جدید
    # ==========================================

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


async def receive_source_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("state") != State.SOURCE_CHANNEL:
        return

    source_channel = update.message.text.strip()
    source_channel = source_channel.strip()

    # =====================================================
    # حالت تغییر مبدا
    # =====================================================

    if context.user_data.get("changing_source"):

        transfer_id = context.user_data.get("change_source_transfer_id")

        if not transfer_id:

            context.user_data["state"] = State.NONE

            await update.message.reply_text("❌ اطلاعات تغییر مبدا پیدا نشد.")

            return

        # ---------------------------------------------
        # عضو شدن در مبدا جدید
        # ---------------------------------------------

        try:

            try:

                await tg_client(JoinChannelRequest(source_channel))

            except UserAlreadyParticipantError:

                pass

        except Exception as e:

            await update.message.reply_text(
                "❌ عضویت اکانت در مبدا جدید انجام نشد.\n\n" f"خطا: {e}"
            )

            return

        # ---------------------------------------------
        # گرفتن انتقال جدید
        # ---------------------------------------------

        transfers = get_user_transfers(update.effective_user.id)

        transfer = None

        for item in transfers:

            if item[0] == transfer_id:

                transfer = item
                break

        if transfer is None:

            context.user_data["state"] = State.NONE

            await update.message.reply_text("❌ انتقال پیدا نشد.")

            return

        target_channel = transfer[2]

        # بروزرسانی مبدا در دیتابیس
        update_transfer_source(
            transfer_id,
            source_channel,
        )

        # ---------------------------------------------
        # ساخت Listener جدید
        # ---------------------------------------------

        if transfer[3]:

            await add_new_transfer(
                update.effective_user.id,
                source_channel,
                target_channel,
            )

        # ---------------------------------------------
        # پاک کردن وضعیت
        # ---------------------------------------------

        context.user_data.pop(
            "change_source_transfer_id",
            None,
        )

        context.user_data.pop(
            "changing_source",
            None,
        )

        context.user_data["state"] = State.NONE

        await update.message.reply_text(
            f"""✅ <b>مبدا با موفقیت تغییر کرد.</b>

📥 مبدا جدید: {source_channel}
📤 مقصد: {target_channel}

📊 وضعیت: {"🟢 فعال" if transfer[3] else "🔴 متوقف"}""",
            parse_mode="HTML",
        )

        return

    # =====================================================
    # ثبت عادی مبدا
    # =====================================================

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

    await update.message.reply_text(
        f"""✅ <b>کانال مبدا ثبت شد.</b>
📥 <b>مبدا:</b> {source_channel}
📤 <b>حالا آیدی کانال مقصد را ارسال کنید.</b>
📝 مثال:
<code>@target_channel</code>""",
        parse_mode="HTML",
    )


# =========================
# receive target channel
# =========================


async def receive_target_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("state") != State.TARGET_CHANNEL:
        return

    target_channel = update.message.text.strip()

    # =====================================================
    # CHANGE TARGET
    # =====================================================

    if context.user_data.get("changing_target"):

        transfer_id = context.user_data.get("change_target_transfer_id")

        if not transfer_id:

            context.user_data["state"] = State.NONE

            await update.message.reply_text("❌ اطلاعات تغییر مقصد پیدا نشد.")

            return

        transfer = get_transfer_by_id(transfer_id)

        if not transfer:

            context.user_data["state"] = State.NONE

            await update.message.reply_text("❌ انتقال پیدا نشد.")

            return

        source_channel = transfer["source_channel"]
        old_target = transfer["target_channel"]
        enabled = bool(transfer["enabled"])

        # =================================================
        # STOP OLD LISTENER
        # =================================================

        try:

            await stop_transfer_listener(
                source_channel,
                old_target,
            )

        except Exception as e:
            pass

        # =================================================
        # JOIN NEW TARGET
        # =================================================

        try:

            try:

                await tg_client(
                    JoinChannelRequest(
                        target_channel,
                    )
                )

            except UserAlreadyParticipantError:

                pass

        except Exception as e:

            if enabled:

                try:

                    await add_new_transfer(
                        update.effective_user.id,
                        source_channel,
                        old_target,
                    )

                except Exception as e:
                    pass

            await update.message.reply_text(
                f"❌ عضویت در مقصد جدید انجام نشد.\n\nخطا: {e}"
            )

            return

        # =================================================
        # GET NEW TARGET
        # =================================================

        try:

            entity = await tg_client.get_entity(target_channel)

        except Exception as e:

            try:
                await tg_client(
                    functions.channels.LeaveChannelRequest(
                        channel=target_channel,
                    )
                )
            except Exception:
                pass

            if enabled:
                try:
                    await add_new_transfer(
                        update.effective_user.id,
                        source_channel,
                        old_target,
                    )
                except Exception as e:
                    pass

            await update.message.reply_text(
                f"❌ امکان دریافت اطلاعات مقصد جدید وجود ندارد.\n\nخطا: {e}"
            )

            return

        context.user_data["pending_change_target"] = transfer_id
        context.user_data["pending_source"] = source_channel
        context.user_data["pending_target"] = target_channel
        context.user_data["old_target"] = old_target
        context.user_data["enabled"] = enabled
        context.user_data["state"] = State.NONE

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ انجام شد",
                    callback_data="finish_change_target",
                )
            ]
        ]

        await update.message.reply_text(
            f"""✅ <b>کانال مقصد ثبت شد.</b>
📥 <b>مبدا:</b> {source_channel}
📤 <b>مقصد جدید:</b> {target_channel}

<b>حالا:
1- ربات رو ادمین کانال مقصد کن.
2- اکانت @egpora_e3 رو هم ادمین کانال مقصد کن.
اگر هر دو ادمین نباشن، انتقال انجام نمیشه.

بعد روی دکمه زیر بزن.</b>""",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        return

    # =====================================================
    # CREATE NEW TRANSFER
    # =====================================================

    source_channel = context.user_data.get("source_channel")

    if not source_channel:

        context.user_data["state"] = State.NONE

        await update.message.reply_text("❌ کانال مبدا پیدا نشد.")

        return

    # =================================================
    # JOIN TARGET
    # =================================================

    try:

        try:
            await tg_client(
                JoinChannelRequest(
                    target_channel,
                )
            )

        except UserAlreadyParticipantError:
            pass

    except Exception as e:

        await update.message.reply_text(
            "❌ عضویت اکانت در کانال مقصد انجام نشد.\n\n" f"خطا: {e}"
        )

        return

    # =================================================
    # SAVE PENDING TRANSFER
    # =================================================

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
        f"""✅ <b>کانال مقصد ثبت شد.</b>
📥 <b>مبدا:</b> {source_channel}
📤 <b>مقصد:</b> {target_channel}

<b>حالا:
1- ربات رو ادمین کانال مقصد کن.
2- اکانت @egpora_e3 رو هم ادمین کانال مقصد کن.
اگر هر دو ادمین نباشن، انتقال انجام نمیشه

بعد روی دکمه زیر بزن.</b>""",
        parse_mode="HTML",
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

    parts = query.data.split("_")
    transfer_id = int(parts[-1])
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
                "🔄 تغییر مبدا",
                callback_data=f"change_source_{transfer_id}",
            ),
            InlineKeyboardButton(
                "🔄 تغییر مقصد",
                callback_data=f"change_target_{transfer_id}",
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
            ),
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


# -------------------- change source callback --------------------


async def change_source_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ بله",
                callback_data=f"confirm_source_{transfer_id}",
            ),
            InlineKeyboardButton(
                "❌ نه",
                callback_data=f"cancel_source_{transfer_id}",
            ),
        ]
    ]

    await query.edit_message_text(
        """⚠️ <b>تغییر کانال مبدا</b>

مطمئنی می‌خوای کانال مبدا فعلی رو تغییر بدی؟

با ادامه دادن:
• اکانت از مبدا فعلی خارج میشه.
• بعد باید مبدا جدید رو وارد کنی.
• انتقال از مبدا جدید ادامه پیدا می‌کنه.

آیا ادامه میدی؟""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# -------------------- cancel source callback --------------------


async def cancel_source_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    await transfer_info(
        update,
        context,
    )


# -------------------- confirm source callback --------------------


async def confirm_source_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    transfers = get_user_transfers(query.from_user.id)

    transfer = None

    for item in transfers:

        if item[0] == transfer_id:

            transfer = item
            break

    if transfer is None:

        await query.edit_message_text("❌ انتقال پیدا نشد.")

        return

    old_source = transfer[1]
    target = transfer[2]

    # -----------------------------------------
    # متوقف کردن Listener قبلی
    # -----------------------------------------

    stopped = await stop_transfer_listener(
        old_source,
        target,
    )

    if not stopped:

        await query.edit_message_text(
            "❌ متوقف کردن انتقال قبلی انجام نشد.\n\n" "لطفاً دوباره تلاش کنید."
        )

        return

    # -----------------------------------------
    # خروج اکانت از مبدا قبلی
    # -----------------------------------------

    try:

        old_entity = await tg_client.get_entity(old_source)

        await tg_client(functions.channels.LeaveChannelRequest(old_entity))

    except Exception:

        pass

        await query.edit_message_text(
            "❌ خروج اکانت از مبدا قبلی انجام نشد.\n\n" "تغییر مبدا انجام نشد."
        )

        return

    # -----------------------------------------
    # آماده دریافت مبدا جدید
    # -----------------------------------------

    context.user_data["change_source_transfer_id"] = transfer_id

    context.user_data["state"] = State.SOURCE_CHANNEL

    context.user_data["changing_source"] = True

    await query.edit_message_text(
        """✅ اکانت با موفقیت از مبدا قبلی خارج شد.

📢 <b>حالا مبدا جدید را ارسال کن.</b>

مثال: <code>@new_source</code>""",
        parse_mode="HTML",
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


async def delete_transfer_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[1])

    transfers = get_user_transfers(query.from_user.id)

    transfer = next(
        (t for t in transfers if t[0] == transfer_id),
        None,
    )

    if not transfer:

        await query.edit_message_text("❌ انتقال پیدا نشد.")

        return

    source_channel = transfer[1]
    target_channel = transfer[2]

    # --------------------------------------------------
    # توقف Listener / Polling
    # --------------------------------------------------

    stopped = await stop_transfer_listener(
        source_channel,
        target_channel,
    )

    if not stopped:

        await query.edit_message_text("❌ توقف انتقال انجام نشد.")

        return

    # --------------------------------------------------
    # خروج از مبدا
    # --------------------------------------------------

    try:

        source_entity = await tg_client.get_entity(source_channel)

        await tg_client(functions.channels.LeaveChannelRequest(source_entity))

    except Exception:

        pass

    # --------------------------------------------------
    # خروج از مقصد
    # --------------------------------------------------

    try:

        target_entity = await tg_client.get_entity(target_channel)

        await tg_client(functions.channels.LeaveChannelRequest(target_entity))

    except Exception:

        pass

    # --------------------------------------------------
    # حذف انتقال از دیتابیس
    # --------------------------------------------------

    delete_transfer(transfer_id)

    await query.edit_message_text(
        """✅ <b>انتقال با موفقیت حذف شد.</b>

اکانت از کانال مبدا و مقصد خارج شد.

حالا می‌توانید یک انتقال جدید ثبت کنید.""",
        parse_mode="HTML",
    )


# -------------------- toggle transfer callback --------------------


async def toggle_transfer_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    transfer_id = int(query.data.split("_")[1])

    transfers = get_user_transfers(query.from_user.id)

    transfer = next(
        (t for t in transfers if t[0] == transfer_id),
        None,
    )

    if not transfer:

        await query.edit_message_text("❌ انتقال پیدا نشد.")

        return

    source_channel = transfer[1]
    target_channel = transfer[2]

    current_enabled = bool(transfer[3])

    # وضعیت جدید
    new_enabled = not current_enabled

    # ==================================================
    # توقف انتقال
    # ==================================================

    if not new_enabled:

        stopped = await stop_transfer_listener(
            source_channel,
            target_channel,
        )

        if not stopped:

            await query.edit_message_text(
                "❌ متوقف کردن انتقال انجام نشد.\n\n" "لطفاً دوباره تلاش کنید."
            )

            return

        # ذخیره وضعیت توقف
        set_transfer_enabled(
            transfer_id,
            False,
        )

    # ==================================================
    # فعال کردن انتقال
    # ==================================================

    else:

        try:

            # ساخت Listener / Polling جدید

            await add_new_transfer(
                query.from_user.id,
                source_channel,
                target_channel,
            )

            set_transfer_enabled(
                transfer_id,
                True,
            )

        except Exception as e:

            # اگر ساخت Listener شکست خورد،
            # انتقال دوباره متوقف شود

            set_transfer_enabled(
                transfer_id,
                False,
            )

            pass

            await query.edit_message_text("❌ فعال‌سازی انتقال انجام نشد.")

            return

    # ==================================================
    # نمایش دوباره اطلاعات انتقال
    # ==================================================

    await transfer_info(
        update,
        context,
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
            ),
            InlineKeyboardButton(
                "➕ افزودن خطوط آخر",
                callback_data=f"append_lines_{transfer_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data=f"transfer_{transfer_id}",
            ),
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

    # بررسی عضویت اکانت در مقصد

    try:

        await tg_client(
            GetParticipantRequest(
                target_channel,
                "me",
            )
        )

    except UserNotParticipantError:

        await query.answer(
            "❌ اکانت داخل کانال مقصد عضو نیست.",
            show_alert=True,
        )

        return

    except Exception:

        pass

        await query.answer(
            "❌ بررسی اکانت در مقصد انجام نشد.",
            show_alert=True,
        )

        return

    # ----------------------------------
    # بررسی وجود و ادمین بودن ربات
    # ----------------------------------

    try:

        me = await context.bot.get_me()

        bot_member = await context.bot.get_chat_member(
            chat_id=target_channel,
            user_id=me.id,
        )

    except Exception:

        await query.message.reply_text(
            "❌ ربات هنوز ادمین کانال مقصد نیست.\n\n"
            "لطفاً ربات را در کانال مقصد ادمین کنید و دوباره روی «انجام شد» بزنید."
        )

        return

    if bot_member.status not in (
        "administrator",
        "creator",
    ):

        await query.message.reply_text(
            "❌ ربات هنوز ادمین کانال مقصد نیست.\n\n"
            "لطفاً ربات را در کانال مقصد ادمین کنید و دوباره روی «انجام شد» بزنید."
        )

        return

    # ----------------------------------
    # بررسی ادمین بودن اکانت شخصی
    # ----------------------------------

    try:

        participant = await tg_client(
            GetParticipantRequest(
                target_channel,
                "me",
            )
        )

        participant = participant.participant

        if type(participant).__name__ not in (
            "ChannelParticipantAdmin",
            "ChannelParticipantCreator",
        ):

            await query.message.reply_text(
                "❌ اکانت هنوز ادمین کانال مقصد نیست.\n\n"
                "لطفاً اکانت را در کانال مقصد ادمین کنید و دوباره روی «انجام شد» بزنید."
            )

            return

    except Exception:

        await query.message.reply_text(
            "❌ امکان بررسی ادمین بودن اکانت وجود ندارد.\n\n"
            "مطمئن شوید اکانت در مقصد عضو و ادمین است."
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

    await add_new_transfer(
        query.from_user.id,
        source_channel,
        target_channel,
    )

    context.user_data.pop("pending_source", None)
    context.user_data.pop("pending_target", None)

    await query.edit_message_text(f"""✅ انتقال ثبت شد.

📥 مبدا: {source_channel}
📤 مقصد: {target_channel}

🚀 انتقال خودکار فعال شد.""")


# -------------------- finish change target --------------------


async def finish_change_target(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    transfer_id = context.user_data.get("pending_change_target")
    source_channel = context.user_data.get("pending_source")
    target_channel = context.user_data.get("pending_target")

    if not transfer_id:
        await query.message.reply_text("❌ اطلاعات تغییر مقصد پیدا نشد.")
        return

    transfer = get_transfer_by_id(transfer_id)

    if not transfer:
        await query.message.reply_text("❌ انتقال پیدا نشد.")
        return

    enabled = transfer["enabled"]

    # ===========================
    # CHECK ACCOUNT ADMIN
    # ===========================

    try:

        participant = await tg_client(
            GetParticipantRequest(
                target_channel,
                "me",
            )
        )

        if not isinstance(
            participant.participant,
            (
                ChannelParticipantAdmin,
                ChannelParticipantCreator,
            ),
        ):

            await query.message.reply_text("❌ اکانت متصل هنوز ادمین کانال مقصد نیست.")
            return

    except Exception:

        pass

        await query.message.reply_text(
            "❌ اکانت متصل هنوز عضو یا ادمین کانال مقصد نیست."
        )
        return

    # ===========================
    # CHECK BOT ADMIN
    # ===========================

    try:

        me = await context.bot.get_me()

        bot_member = await context.bot.get_chat_member(
            chat_id=target_channel,
            user_id=me.id,
        )

        if bot_member.status not in (
            "administrator",
            "creator",
        ):

            await query.message.reply_text(
                "❌ ربات هنوز ادمین کانال مقصد نیست.\n\n"
                "ابتدا ربات را ادمین کنید و تمام دسترسی‌ها را فعال کنید."
            )
            return

    except Exception:

        pass

        await query.message.reply_text("❌ ربات هنوز عضو یا ادمین کانال مقصد نیست.")
        return

    # ===========================
    # SAVE
    # ===========================

    update_transfer_target(
        transfer_id,
        target_channel,
    )

    if enabled:

        await add_new_transfer(
            transfer["telegram_id"],
            source_channel,
            target_channel,
        )

    context.user_data.pop(
        "pending_change_target",
        None,
    )
    context.user_data.pop(
        "pending_source",
        None,
    )
    context.user_data.pop(
        "pending_target",
        None,
    )

    context.user_data["state"] = State.NONE

    await query.edit_message_text(f"""✅ مقصد با موفقیت تغییر کرد.

📥 مبدا: {source_channel}
📤 مقصد: {target_channel}

🚀 انتقال ادامه پیدا کرد.""")


# -------------------- change target callback --------------------


async def change_target_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    transfer = get_transfer_by_id(transfer_id)

    if not transfer:

        await query.edit_message_text("❌ انتقال پیدا نشد.")

        return

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ بله",
                callback_data=f"confirm_target_{transfer_id}",
            ),
            InlineKeyboardButton(
                "❌ نه",
                callback_data=f"cancel_target_{transfer_id}",
            ),
        ]
    ]

    await query.edit_message_text(
        """⚠️ <b>تغییر کانال مقصد</b>

مطمئنی می‌خوای کانال مقصد فعلی رو تغییر بدی؟

با ادامه دادن:
• اکانت از مقصد فعلی خارج میشه.
• بعد باید مقصد جدید رو وارد کنی.
• در صورت فعال بودن انتقال، انتقال روی مقصد جدید ادامه پیدا می‌کنه.

آیا ادامه میدی؟""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# -------------------- confirm target callback --------------------


async def confirm_target_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    transfer_id = int(query.data.split("_")[2])

    transfer = get_transfer_by_id(transfer_id)

    if not transfer:

        await query.edit_message_text("❌ انتقال پیدا نشد.")

        return

    source_channel = transfer["source_channel"]

    target_channel = transfer["target_channel"]

    # -------------------------------------------------
    # توقف Listener / Polling قبلی
    # -------------------------------------------------

    stopped = await stop_transfer_listener(
        source_channel,
        target_channel,
    )

    if not stopped:

        await query.edit_message_text(
            "❌ متوقف کردن انتقال قبلی انجام نشد.\n\n" "لطفاً دوباره تلاش کنید."
        )

        return

    # -------------------------------------------------
    # خروج از مقصد قبلی
    # -------------------------------------------------

    try:

        target_entity = await tg_client.get_entity(target_channel)

        await tg_client(functions.channels.LeaveChannelRequest(target_entity))

    except Exception as e:

        await query.edit_message_text(
            "❌ خروج اکانت از مقصد قبلی انجام نشد.\n\n" f"خطا: {e}"
        )

        return

    # -------------------------------------------------
    # ذخیره وضعیت تغییر مقصد
    # -------------------------------------------------

    context.user_data["changing_target"] = True

    context.user_data["change_target_transfer_id"] = transfer_id

    context.user_data["state"] = State.TARGET_CHANNEL

    await query.edit_message_text(
        """✅ اکانت با موفقیت از مقصد قبلی خارج شد.

📢 <b>حالا مقصد جدید رو ارسال کن.</b>
مثال: <code>@new_target</code>""",
        parse_mode="HTML",
    )


# -------------------- cancel target callback --------------------


async def cancel_target_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    context.user_data.pop(
        "change_target_transfer_id",
        None,
    )

    context.user_data.pop(
        "changing_target",
        None,
    )

    context.user_data["state"] = State.NONE

    await transfer_info(
        update,
        context,
    )
