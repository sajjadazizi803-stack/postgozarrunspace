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
from database import get_user_transfer_count

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

from telethon import TelegramClient
from telethon.sessions import StringSession
from database import get_account

from telethon.tl.types import (
    ChannelParticipantAdmin,
    ChannelParticipantCreator,
)

change_target_states = {}

# ---------------------- get user telegram client ----------------------


async def get_user_telegram_client(user_id):

    account = get_account(user_id)

    if not account:
        return None

    api_id = account[1]
    api_hash = account[2]
    session_string = account[4]

    if not api_id or not api_hash or not session_string:
        return None

    try:

        client = TelegramClient(
            StringSession(session_string),
            int(api_id),
            api_hash,
        )

        await client.connect()

        if not await client.is_user_authorized():

            await client.disconnect()

            return None

        return client

    except Exception as e:

        print(
            "[USER SESSION ERROR]",
            e,
        )

        return None


# =========================
# connect account
# =========================


async def connect_account(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    account_type = context.user_data.get(
        "transfer_account_type",
        context.user_data.get(
            "account_type",
            "user",
        ),
    )

    context.user_data["account_type"] = account_type
    context.user_data["client_type"] = account_type

    # ==========================================
    # اگر انتقال با اکانت شخصی است
    # اول بررسی کنیم اکانت وصل شده یا نه
    # ==========================================

    if account_type == "user":

        from database import get_account

        account = get_account(user_id)

        # اگر اطلاعات اکانت وجود ندارد
        if not account:

            await update.message.reply_text(
                """⚠️ هنوز اکانتت رو به ربات وصل نکردی.

اول از بخش «📲 اتصال اکانت» اکانتت رو به ربات وصل کن، بعد دوباره از قسمت «➕ افزودن انتقال» با اکانت خودت انتقال ثبت کن."""
            )

            context.user_data["state"] = State.NONE

            return

        # بررسی API ID
        api_id = account[1] if len(account) > 1 else None

        # بررسی API HASH
        api_hash = account[2] if len(account) > 2 else None

        # بررسی شماره
        phone = account[3] if len(account) > 3 else None

        if not api_id or not api_hash or not phone:

            await update.message.reply_text(
                """⚠️ هنوز اتصال اکانتت کامل نشده.

اول از بخش «📲 اتصال اکانت» مراحل اتصال اکانت رو کامل کن، بعد دوباره انتقال رو ثبت کن."""
            )

            context.user_data["state"] = State.NONE

            return

    # ==========================================
    # محدودیت تعداد انتقال
    # ==========================================

    transfer_count = get_user_transfer_count(
        user_id,
        account_type,
    )

    # اکانت ربات فقط 1 انتقال
    if account_type == "bot" and transfer_count >= 1:

        text = (
            "⚠️ <b>شما قبلاً یک انتقال با اکانت ربات ثبت کرده‌اید.</b>\n\n"
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

    # اکانت شخصی حداکثر 5 انتقال
    if account_type == "user" and transfer_count >= 5:

        text = (
            "⚠️ <b>به حداکثر تعداد انتقال رسیده‌اید.</b>\n\n"
            "با اکانت شخصی حداکثر ۵ انتقال می‌توانید ثبت کنید."
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
    # شروع ثبت انتقال
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

    account_type = context.user_data.get(
        "transfer_account_type",
        "user",
    )

    context.user_data["account_type"] = account_type
    context.user_data["client_type"] = account_type

    print(
        "[TRANSFER ACCOUNT]",
        account_type,
    )

    if not update.message or not update.message.text:
        return

    source_channel = update.message.text.strip()

    if source_channel in (
        "🤖 با اکانت ربات",
        "👤 با اکانت خودم",
        "📢 کانال",
        "👥 گروه",
        "🏠",
        "🔙",
    ):
        return

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
    # ثبت مبدا
    # =====================================================

    account_type = context.user_data.get(
        "transfer_account_type",
        "bot",
    )

    if account_type == "user":

        user_client = await get_user_telegram_client(update.effective_user.id)

        if not user_client:

            await update.message.reply_text(
                "❌ اتصال اکانتت پیدا نشد یا نشست اکانت معتبر نیست.\n\n"
                "اول از بخش «📲 اتصال اکانت» دوباره اکانتت رو وصل کن."
            )

            context.user_data["state"] = State.NONE

            return

        try:

            try:

                await user_client(JoinChannelRequest(source_channel))

            except UserAlreadyParticipantError:

                pass

        except Exception as e:

            await update.message.reply_text(
                "❌ اکانت شما نتونست وارد کانال مبدا بشه.\n\n" f"خطا: {e}"
            )

            await user_client.disconnect()

            return

        await user_client.disconnect()

    else:

        try:

            try:

                await tg_client(JoinChannelRequest(source_channel))

            except UserAlreadyParticipantError:

                pass

        except Exception as e:

            await update.message.reply_text(
                "❌ عضویت ربات در کانال مبدا انجام نشد.\n\n" f"خطا: {e}"
            )

            return

    context.user_data["source_channel"] = source_channel
    context.user_data["state"] = State.TARGET_CHANNEL

    await update.message.reply_text(
        f"""✅ <b>کانال مبدا ثبت شد.</b>
📥 <b>مبدا:</b> {source_channel}
📤 <b>حالا آیدی کانال مقصد را ارسال کنید.</b>
📝 مثال: @target_channel""",
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

    account_type = context.user_data.get(
        "client_type",
        context.user_data.get(
            "account_type",
            "user",
        ),
    )

    context.user_data["account_type"] = account_type
    context.user_data["use_bot_session"] = account_type == "bot"

    print(
        "[TRANSFER ACCOUNT]",
        account_type,
    )

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

    account_type = context.user_data.get(
        "transfer_account_type",
        "bot",
    )

    if account_type == "user":

        user_client = await get_user_telegram_client(update.effective_user.id)

        if not user_client:

            await update.message.reply_text(
                "❌ اتصال اکانتت پیدا نشد یا نشست اکانت معتبر نیست.\n\n"
                "اول از بخش «📲 اتصال اکانت» دوباره اکانتت رو وصل کن."
            )

            context.user_data["state"] = State.NONE

            return

        try:

            try:

                await user_client(
                    JoinChannelRequest(
                        target_channel,
                    )
                )

            except UserAlreadyParticipantError:

                pass

        except Exception as e:

            await update.message.reply_text(
                "❌ اکانت شما نتونست وارد کانال مقصد بشه.\n\n" f"خطا: {e}"
            )

            await user_client.disconnect()

            return

        await user_client.disconnect()

    else:

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
                "❌ عضویت ربات در کانال مقصد انجام نشد.\n\n" f"خطا: {e}"
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

    if account_type == "bot":

        admin_text = """🤖 حالا اکانت زیر را در کانال مقصد ادمین کنید:
@egpora_e3

بعد از ادمین کردن اکانت، روی «✅ انجام شد» بزنید."""

    else:

        admin_text = """👤 حالا همان اکانتی که به ربات وصل کرده‌اید را در کانال مقصد ادمین کنید.

بعد از ادمین کردن اکانت، روی «✅ انجام شد» بزنید."""

    await update.message.reply_text(
        f"""✅ <b>کانال مقصد ثبت شد.</b>

📥 <b>مبدا:</b> {source_channel}
📤 <b>مقصد:</b> {target_channel}

{admin_text}""",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------------------- registered channels --------------------


async def registered_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    transfers = get_user_transfers(user_id)

    if not transfers:
        await update.message.reply_text("❌ هنوز هیچ انتقالی ثبت نکرده‌اید.")
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


async def finish_transfer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    source_channel = context.user_data.get("pending_source")

    target_channel = context.user_data.get("pending_target")

    account_type = context.user_data.get(
        "transfer_account_type",
        context.user_data.get(
            "account_type",
            "bot",
        ),
    )

    if not source_channel or not target_channel:

        await query.edit_message_text("❌ اطلاعات انتقال پیدا نشد.")

        return

    # =====================================================
    # انتقال با اکانت شخصی
    # =====================================================

    if account_type == "user":

        user_client = await get_user_telegram_client(user_id)

        if not user_client:

            await query.message.reply_text(
                """❌ اتصال اکانتت پیدا نشد یا نشست اکانت معتبر نیست.

اول از بخش «📲 اتصال اکانت» دوباره اکانتت رو وصل کن."""
            )

            return

        # -------------------------------------------------
        # بررسی عضویت اکانت کاربر در مبدأ
        # -------------------------------------------------

        try:

            await user_client(
                GetParticipantRequest(
                    source_channel,
                    "me",
                )
            )

        except UserNotParticipantError:

            await user_client.disconnect()

            await query.message.reply_text(
                """❌ اکانت شما هنوز داخل کانال مبدا عضو نیست.

ابتدا مطمئن شوید اکانت شما عضو کانال مبدا شده باشد."""
            )

            return

        except Exception as e:

            print(
                "[USER SOURCE CHECK ERROR]",
                e,
            )

            await user_client.disconnect()

            await query.message.reply_text(
                """❌ امکان بررسی عضویت اکانت در کانال مبدا وجود ندارد.

لطفاً دوباره تلاش کنید."""
            )

            return

        # -------------------------------------------------
        # بررسی عضویت اکانت کاربر در مقصد
        # -------------------------------------------------

        try:

            await user_client(
                GetParticipantRequest(
                    target_channel,
                    "me",
                )
            )

        except UserNotParticipantError:

            await user_client.disconnect()

            await query.message.reply_text(
                """❌ اکانت شما هنوز داخل کانال مقصد عضو نیست.

لطفاً مطمئن شوید اکانت شما عضو کانال مقصد شده باشد."""
            )

            return

        except Exception as e:

            print(
                "[USER TARGET CHECK ERROR]",
                e,
            )

            await user_client.disconnect()

            await query.message.reply_text(
                """❌ امکان بررسی عضویت اکانت در کانال مقصد وجود ندارد.

لطفاً دوباره تلاش کنید."""
            )

            return

        # Session دیگر لازم نیست
        await user_client.disconnect()

    # =====================================================
    # انتقال با اکانت ربات
    # =====================================================

    else:

        # -------------------------------------------------
        # بررسی عضویت ربات در مبدأ
        # -------------------------------------------------

        try:

            await tg_client(
                GetParticipantRequest(
                    source_channel,
                    "me",
                )
            )

        except UserNotParticipantError:

            await query.message.reply_text("❌ ربات داخل کانال مبدا عضو نیست.")

            return

        except Exception as e:

            print(
                "[BOT SOURCE CHECK ERROR]",
                e,
            )

        # -------------------------------------------------
        # بررسی عضویت ربات در مقصد
        # -------------------------------------------------

        try:

            await tg_client(
                GetParticipantRequest(
                    target_channel,
                    "me",
                )
            )

        except UserNotParticipantError:

            await query.message.reply_text("❌ ربات داخل کانال مقصد عضو نیست.")

            return

        except Exception as e:

            print(
                "[BOT TARGET CHECK ERROR]",
                e,
            )

    # =====================================================
    # بررسی ادمین بودن اکانت ارسال کننده
    # =====================================================

    if account_type == "bot":

        # اکانت ثابت متصل به پروژه
        # باید ادمین مقصد باشد

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

                await query.message.reply_text(
                    """❌ اکانت متصل به ربات هنوز ادمین کانال مقصد نیست.

لطفاً اکانت @egpora_e3 را در کانال مقصد ادمین کنید.

بعد دوباره روی «✅ انجام شد» بزنید."""
                )

                return

        except Exception as e:

            print(
                "[BOT ACCOUNT ADMIN CHECK]",
                e,
            )

            await query.message.reply_text(
                """❌ اکانت @egpora_e3 هنوز ادمین کانال مقصد نیست.

لطفاً ابتدا آن را ادمین کنید و دوباره روی «✅ انجام شد» بزنید."""
            )

            return

    else:

        # =================================================
        # اکانت شخصی خود کاربر
        # =================================================

        user_client = await get_user_telegram_client(user_id)

        if not user_client:

            await query.message.reply_text("""❌ اتصال اکانت شما پیدا نشد.

ابتدا اکانت خودتان را از بخش «📲 اتصال اکانت» وصل کنید.""")

            return

        try:

            participant = await user_client(GetParticipantRequest(target_channel, "me"))

            if not isinstance(
                participant.participant,
                (
                    ChannelParticipantAdmin,
                    ChannelParticipantCreator,
                ),
            ):

                await user_client.disconnect()

                await query.message.reply_text(
                    """❌ اکانت شما هنوز ادمین کانال مقصد نیست.

لطفاً همان اکانتی که به ربات وصل کرده‌اید را در کانال مقصد ادمین کنید.

بعد دوباره روی «✅ انجام شد» بزنید."""
                )

                return

        except Exception as e:

            print(
                "[USER ACCOUNT ADMIN CHECK]",
                e,
            )

            await user_client.disconnect()

            await query.message.reply_text("""❌ اکانت شما هنوز ادمین کانال مقصد نیست.

لطفاً اکانت متصل خودتان را ادمین کنید و دوباره روی «✅ انجام شد» بزنید.""")

            return

        await user_client.disconnect()

    # =====================================================
    # ثبت انتقال
    # =====================================================

    try:

        add_transfer(
            user_id,
            source_channel,
            target_channel,
            account_type,
        )

    except Exception as e:

        print(
            "[ADD TRANSFER ERROR]",
            e,
        )

        await query.message.reply_text("❌ ثبت انتقال انجام نشد.")

        return

    # =====================================================
    # فعال کردن Listener
    # =====================================================

    try:

        await add_new_transfer(
            user_id,
            source_channel,
            target_channel,
        )

    except Exception as e:

        print(
            "[LISTENER START ERROR]",
            e,
        )

        await query.message.reply_text(
            """⚠️ انتقال ثبت شد، اما فعال‌سازی انتقال خودکار با مشکل مواجه شد.

لطفاً وضعیت انتقال را از بخش «📋 انتقال‌های ثبت شده» بررسی کن."""
        )

        return

    # =====================================================
    # پاک کردن اطلاعات موقت
    # =====================================================

    context.user_data.pop(
        "pending_source",
        None,
    )

    context.user_data.pop(
        "pending_target",
        None,
    )

    context.user_data["state"] = State.NONE

    # =====================================================
    # پیام موفقیت
    # =====================================================

    await query.edit_message_text(
        f"""✅ <b>انتقال با موفقیت ثبت شد.</b>

📥 <b>مبدا:</b> {source_channel}
📤 <b>مقصد:</b> {target_channel}

🚀 انتقال خودکار فعال شد.""",
        parse_mode="HTML",
    )


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
