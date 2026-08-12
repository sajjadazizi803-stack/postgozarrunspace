from telegram import Update
from telegram.ext import ContextTypes
from conversation import State
from database import add_transfer, add_registered_group
from listener import (
    add_new_transfer,
    stop_transfer_listener,
)
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

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
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import InputPeerChannel

from database import (
    delete_transfer,
    set_transfer_enabled,
    get_user_transfers,
    get_user_groups,
    get_remove_last_lines,
    set_append_last_lines,
    get_append_last_lines,
    update_transfer_source,
    update_transfer_target,
    get_transfer_by_id,
    save_group_message,
    get_group_message,
    set_group_schedule,
    delete_registered_group,
    set_group_enabled,
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

        pass

        return None


# ---------------------- show group info panel -----------------


async def show_group_info_panel(
    context,
    chat_id,
    group_db_id,
    user_id,
    old_message_id=None,
):
    """
    پنل مدیریت گروه را نمایش می‌دهد.
    اگر پیام قبلی وجود داشته باشد، همان پیام Edit می‌شود.
    """

    groups = get_user_groups(user_id)

    group = None

    for item in groups:

        if item[0] == group_db_id:

            group = item

            break

    if group is None:

        return None

    title = group[3]

    username = group[4]

    group_id = group[1]

    enabled = bool(group[6])

    username_text = f"@{username}" if username else "ندارد"

    status = "🟢 فعال" if enabled else "🔴 متوقف"

    # -----------------------------------------
    # اطلاعات پیام و زمان‌بندی
    # -----------------------------------------

    group_message = get_group_message(
        group_db_id,
        user_id,
    )

    if group_message:

        message_status = "✅ ثبت شده"

        schedule_minutes = group_message[9]

        if schedule_minutes:

            schedule_text = f"{schedule_minutes} دقیقه"

        else:

            schedule_text = "نامشخص"

    else:

        message_status = "❌ ثبت نشده"

        schedule_text = "نامشخص"

    # -----------------------------------------
    # دکمه‌ها
    # -----------------------------------------

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 پیام / بنر",
                callback_data=(f"group_message_{group_db_id}"),
            )
        ],
        [
            InlineKeyboardButton(
                "⏱ زمان‌بندی",
                callback_data=(f"group_schedule_{group_db_id}"),
            ),
            InlineKeyboardButton(
                "🗑 حذف گروه",
                callback_data=(f"delete_group_{group_db_id}"),
            ),
        ],
        [
            InlineKeyboardButton(
                ("⏹ توقف تبلیغات" if enabled else "▶️ شروع تبلیغات"),
                callback_data=(f"start_group_ads_{group_db_id}"),
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="registered_group",
            )
        ],
    ]

    panel_text = f"""📢 <b>اطلاعات گروه</b>

👥 <b>گروه:</b> {title}
🔗 <b>یوزرنیم:</b> {username_text}
🆔 <b>شناسه:</b> {group_id}
📝 <b>پیام تبلیغ:</b> {message_status}
⏱ <b>فاصله ارسال:</b> {schedule_text}

📊 <b>وضعیت:</b> {status}"""

    # -----------------------------------------
    # اگر پیام قبلی وجود دارد → همان را Edit کن
    # -----------------------------------------

    if old_message_id:

        try:

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=old_message_id,
                text=panel_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML",
            )

            context.user_data["group_info_message_id"] = old_message_id

            return old_message_id

        except Exception as e:

            print(
                "[GROUP PANEL EDIT ERROR]",
                e,
            )

    # -----------------------------------------
    # اگر پیام قبلی وجود ندارد → پیام جدید بساز
    # -----------------------------------------

    message = await context.bot.send_message(
        chat_id=chat_id,
        text=panel_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )

    context.user_data["group_info_message_id"] = message.message_id

    return message.message_id


# =========================
# START GROUP REGISTRATION
# =========================


async def start_group_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id

    # -----------------------------------------
    # بررسی اتصال اکانت کاربر
    # -----------------------------------------

    user_client = await get_user_telegram_client(user_id)

    if not user_client:

        await update.message.reply_text(
            """❌ برای استفاده از بخش گروه، ابتدا باید اکانت خودتان را به ربات وصل کنید.

از بخش «📲 اتصال اکانت» اکانت خودتان را وصل کنید و سپس دوباره وارد بخش «👥 گروه» شوید."""
        )

        context.user_data["state"] = State.NONE

        return

    await user_client.disconnect()

    # -----------------------------------------
    # ورود به مرحله دریافت گروه
    # -----------------------------------------

    context.user_data["state"] = State.GROUP

    await update.message.reply_text(
        """
لینک یا یوزرنیم گروهی که می‌خواهید ثبت کنید را ارسال کنید.""",
        parse_mode="HTML",
    )


# =========================
# RECEIVE GROUP
# =========================


async def receive_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("state") != State.GROUP:
        return

    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id

    group_link = update.message.text.strip()

    # -----------------------------------------
    # دوباره بررسی اتصال اکانت
    # -----------------------------------------

    user_client = await get_user_telegram_client(user_id)

    if not user_client:

        context.user_data["state"] = State.NONE

        await update.message.reply_text("""❌ اتصال اکانت شما پیدا نشد.

ابتدا اکانت خودتان را از بخش «📲 اتصال اکانت» وصل کنید.""")

        return

    try:

        entity = None

        # -----------------------------------------
        # لینک دعوت خصوصی
        # -----------------------------------------

        if "t.me/+" in group_link:

            invite_hash = (
                group_link.split(
                    "t.me/+",
                    1,
                )[1]
                .split(
                    "?",
                    1,
                )[0]
                .strip("/")
            )

            result = await user_client(ImportChatInviteRequest(invite_hash))

            if getattr(result, "chats", None):

                entity = result.chats[0]

        # -----------------------------------------
        # لینک دعوت قدیمی
        # -----------------------------------------

        elif "t.me/joinchat/" in group_link:

            invite_hash = (
                group_link.split(
                    "t.me/joinchat/",
                    1,
                )[1]
                .split(
                    "?",
                    1,
                )[0]
                .strip("/")
            )

            result = await user_client(ImportChatInviteRequest(invite_hash))

            if getattr(result, "chats", None):

                entity = result.chats[0]

        # -----------------------------------------
        # گروه عمومی
        # -----------------------------------------

        else:

            entity = await user_client.get_entity(group_link)

            try:

                await user_client(JoinChannelRequest(entity))

            except UserAlreadyParticipantError:

                pass

        # -----------------------------------------
        # بررسی اینکه واقعاً گروه باشد
        # -----------------------------------------

        if entity is None:

            raise RuntimeError("GROUP_NOT_FOUND")

        # Telegram supergroup معمولاً Channel
        # با megagroup=True است

        if not getattr(
            entity,
            "megagroup",
            False,
        ):

            await user_client.disconnect()

            await update.message.reply_text(
                """❌ لینکی که فرستادید مربوط به یک گروه نیست.

لطفاً لینک یا یوزرنیم یک گروه تلگرامی ارسال کنید."""
            )

            return

        # -----------------------------------------
        # اطلاعات گروه
        # -----------------------------------------

        group_id = entity.id

        access_hash = getattr(
            entity,
            "access_hash",
            None,
        )

        title = getattr(
            entity,
            "title",
            "بدون نام",
        )

        username = getattr(
            entity,
            "username",
            None,
        )

        # -----------------------------------------
        # ذخیره گروه
        # -----------------------------------------

        add_registered_group(
            user_id=user_id,
            group_id=group_id,
            access_hash=access_hash,
            title=title,
            username=username,
            group_link=group_link,
        )

        await user_client.disconnect()

        context.user_data["state"] = State.NONE

        await update.message.reply_text(
            f"""✅ <b>گروه با موفقیت ثبت شد.</b>

👥 <b>گروه:</b> {title}
📌 <b>لینک:</b> {group_link}

برای ادامه و تنظیم پیام و زمان‌بندی ارسال، بعداً از بخش: 📋 <b>انتقال‌های ثبت شده</b>
گروه خود را مدیریت کنید.""",
            parse_mode="HTML",
        )

        return

    except Exception as e:

        print(
            "[GROUP REGISTRATION ERROR]",
            e,
        )

        try:

            await user_client.disconnect()

        except Exception:

            pass

        await update.message.reply_text(
            """❌ ثبت گروه انجام نشد.

مطمئن شوید لینکی که فرستادید مربوط به یک گروه تلگرامی معتبر است و اکانت متصل شما به آن گروه دسترسی دارد."""
        )

        return


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


async def registered_channels(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data["transfer_menu"] = "REGISTERED"

    keyboard = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("📢 کانال"),
                KeyboardButton("👥 گروه"),
            ],
            [
                KeyboardButton("🔙"),
            ],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        """📋 <b>انتقال‌های ثبت شده</b>

لطفاً نوع انتقالی که می‌خواهید مدیریت کنید را انتخاب کنید:""",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# -------------------- registered channels from keyboard --------------------


async def registered_channels_from_keyboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # همچنان داخل منوی «انتقال‌های ثبت شده» هستیم
    context.user_data["transfer_menu"] = "REGISTERED"

    transfers = get_user_transfers(update.effective_user.id)

    if not transfers:

        await update.message.reply_text("""❌ هنوز هیچ کانالی ثبت نکرده‌اید.""")

        return

    keyboard = []

    for transfer in transfers:

        transfer_id = transfer[0]
        source = transfer[1]
        target = transfer[2]

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{source} ➜ {target}",
                    callback_data=f"transfer_{transfer_id}",
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

    return


# -------------------- registered groups from keyboard --------------------


async def registered_groups_from_keyboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # همچنان داخل منوی «انتقال‌های ثبت شده» هستیم
    context.user_data["transfer_menu"] = "REGISTERED"

    groups = get_user_groups(update.effective_user.id)

    if not groups:

        await update.message.reply_text("""❌ هنوز هیچ گروهی ثبت نکرده‌اید.""")

        return

    keyboard = []

    for group in groups:

        group_db_id = group[0]
        title = group[3]

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"👥 {title}",
                    callback_data=f"registered_group_{group_db_id}",
                )
            ]
        )

    await update.message.reply_text(
        """<b>📋 گروه‌های ثبت‌شده شما</b>

🎯 تمام گروه‌هایی که برای ارسال زمان‌بندی‌شده ثبت کرده‌اید در این بخش نمایش داده می‌شوند.

👇 برای مشاهده اطلاعات هر گروه، روی گروه موردنظر بزنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )

    return


# -------------------- registered channels list --------------------


async def registered_channels_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    transfers = get_user_transfers(query.from_user.id)

    if not transfers:

        await query.edit_message_text(
            """❌ هنوز هیچ کانالی ثبت نکرده‌اید.""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="registered_back",
                        )
                    ]
                ]
            ),
        )

        return

    keyboard = []

    for transfer in transfers:

        transfer_id = transfer[0]
        source = transfer[1]
        target = transfer[2]

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{source} ➜ {target}",
                    callback_data=f"transfer_{transfer_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="registered_back",
            )
        ]
    )

    await query.edit_message_text(
        """<b>📋 کانال‌های ثبت‌شده شما</b>

🎯 تمام اتصال‌های فعال شما در این بخش نمایش داده می‌شوند.

👇 برای مشاهده اطلاعات هر اتصال، کافی است روی دکمه <b>کانال مبدا ➜ مقصد</b> موردنظر بزنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# -------------------- registered groups list --------------------


async def registered_groups_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    groups = get_user_groups(query.from_user.id)

    if not groups:

        await query.edit_message_text("""❌ هنوز هیچ گروهی ثبت نکرده‌اید.""")

        return

    keyboard = []

    for group in groups:

        group_db_id = group[0]
        title = group[3]

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"👥 {title}",
                    callback_data=f"registered_group_{group_db_id}",
                )
            ]
        )

    await query.edit_message_text(
        """<b>📋 گروه‌های ثبت‌شده شما</b>

🎯 تمام گروه‌هایی که برای ارسال زمان‌بندی‌شده ثبت کرده‌اید در این بخش نمایش داده می‌شوند.

👇 برای مشاهده اطلاعات هر گروه، روی گروه موردنظر بزنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# -------------------- registered group info --------------------


async def registered_group_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    user_id = query.from_user.id

    groups = get_user_groups(user_id)

    group_exists = False

    for group in groups:

        if group[0] == group_db_id:

            group_exists = True

            break

    if not group_exists:

        await query.message.reply_text("❌ گروه پیدا نشد.")

        return

    # پنل فعلی را به عنوان پنل مدیریت ذخیره کن
    context.user_data["group_info_message_id"] = query.message.message_id

    # پنل جدید را پایین چت بساز
    await show_group_info_panel(
        context=context,
        chat_id=query.message.chat_id,
        group_db_id=group_db_id,
        user_id=user_id,
        old_message_id=query.message.message_id,
    )

    return


# ------------------------ delete group callback ------------------


async def delete_group_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    user_id = query.from_user.id

    # بررسی اینکه گروه واقعاً متعلق به همین کاربر است
    groups = get_user_groups(user_id)

    group = None

    for item in groups:

        if item[0] == group_db_id:

            group = item

            break

    if group is None:

        await query.message.reply_text("❌ گروه پیدا نشد.")

        return

    title = group[3]

    keyboard = [
        [
            InlineKeyboardButton(
                "🗑 بله، حذف کن",
                callback_data=(f"confirm_delete_group_{group_db_id}"),
            ),
            InlineKeyboardButton(
                "❌ لغو",
                callback_data=(f"cancel_delete_group_{group_db_id}"),
            ),
        ],
    ]

    await query.edit_message_text(
        f"""⚠️ <b>حذف گروه</b>

آیا مطمئن هستید که می‌خواهید گروه:

👥 <b>{title}</b>

را حذف کنید؟

با حذف گروه، تمام اطلاعات مربوط به گروه حذف خواهند شد.""",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------- confirm delete group callback --------------------


async def confirm_delete_group_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    user_id = query.from_user.id

    # دوباره بررسی مالکیت
    groups = get_user_groups(user_id)

    group_exists = False

    for group in groups:

        if group[0] == group_db_id:

            group_exists = True

            break

    if not group_exists:

        await query.message.reply_text("❌ گروه پیدا نشد.")

        return

    delete_registered_group(
        group_db_id,
        user_id,
    )

    await query.edit_message_text(
        """✅ <b>گروه با موفقیت حذف شد.</b>

گروه، پیام/بنر ذخیره‌شده و تنظیمات مربوط به آن حذف شدند.""",
        parse_mode="HTML",
    )


# --------------------- cancel delete group callback -----------------


async def cancel_delete_group_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    user_id = query.from_user.id

    groups = get_user_groups(user_id)

    group = None

    for item in groups:

        if item[0] == group_db_id:

            group = item

            break

    if group is None:

        await query.edit_message_text("❌ گروه پیدا نشد.")

        return

    # همان صفحه اطلاعات گروه را دوباره بساز
    title = group[3]

    username = group[4]

    group_id = group[1]

    enabled = bool(group[6])

    username_text = f"@{username}" if username else "ندارد"

    status = "🟢 فعال" if enabled else "🔴 متوقف"

    group_message = get_group_message(
        group_db_id,
        user_id,
    )

    if group_message:

        schedule_minutes = group_message[9]

        schedule_text = f"{schedule_minutes} دقیقه" if schedule_minutes else "نامشخص"

    else:

        schedule_text = "نامشخص"

    keyboard = [
        [
            InlineKeyboardButton(
                "📝 پیام / بنر",
                callback_data=f"group_message_{group_db_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "⏱ زمان‌بندی",
                callback_data=f"group_schedule_{group_db_id}",
            ),
            InlineKeyboardButton(
                "🗑 حذف گروه",
                callback_data=f"delete_group_{group_db_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="registered_group",
            )
        ],
    ]

    await query.edit_message_text(
        f"""📢 <b>اطلاعات گروه</b>

👥 <b>گروه:</b> {title}
🔗 <b>یوزرنیم:</b> {username_text}
🆔 <b>شناسه:</b> {group_id}
⏱ <b>فاصله ارسال:</b> {schedule_text}

📊 <b>وضعیت:</b> {status}""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# =========================
# GROUP message callback
# =========================


async def group_message_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    groups = get_user_groups(query.from_user.id)

    group_exists = False

    for group in groups:

        if group[0] == group_db_id:

            group_exists = True

            break

    if not group_exists:

        await query.edit_message_text("❌ گروه پیدا نشد.")

        return

    # شناسه پیامی که اطلاعات گروه را نشان می‌دهد
    context.user_data["group_info_message_id"] = query.message.message_id

    context.user_data["group_message_group_id"] = group_db_id

    context.user_data["state"] = State.GROUP_MESSAGE

    prompt = await query.message.reply_text(
        """📩 <b>پیام یا بنری که می‌خواهید در گروه ارسال شود را همینجا بفرستید.</b>

هر نوع پیامی که ارسال کنید برای این گروه ذخیره می‌شود.

📝 متن
🖼 عکس
🎥 ویدئو
📁 فایل
🎵 صوت
و سایر رسانه‌های پشتیبانی‌شده.

اگر پیام را به صورت فوروارد ارسال کنید، در صورت امکان همان حالت فوروارد برای ارسال بعدی حفظ می‌شود.""",
        parse_mode="HTML",
    )

    context.user_data["group_message_prompt_id"] = prompt.message_id


# -------------------- receive group message --------------------


async def receive_group_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if context.user_data.get("state") != State.GROUP_MESSAGE:

        return

    if not update.message:

        return

    user_id = update.effective_user.id

    group_db_id = context.user_data.get("group_message_group_id")

    if not group_db_id:

        context.user_data["state"] = State.NONE

        await update.message.reply_text("❌ اطلاعات گروه پیدا نشد.")

        return

    message = update.message

    message_type = None

    message_text = message.text

    caption = message.caption

    file_path = None

    forward_chat_id = None

    forward_message_id = None

    # ==========================================
    # بررسی فوروارد
    # ==========================================

    forward_origin = getattr(
        message,
        "forward_origin",
        None,
    )

    if forward_origin:

        origin_chat = getattr(
            forward_origin,
            "chat",
            None,
        )

        origin_message_id = getattr(
            forward_origin,
            "message_id",
            None,
        )

        if origin_chat and origin_message_id:

            forward_chat_id = origin_chat.id

            forward_message_id = origin_message_id

            message_type = "forward"

    # ==========================================
    # پیام متنی
    # ==========================================

    if message_type is None and message.text:

        message_type = "text"

    # ==========================================
    # رسانه
    # ==========================================

    if message_type is None:

        media = None

        extension = ".bin"

        if message.photo:

            media = message.photo[-1]

            message_type = "photo"

            extension = ".jpg"

        elif message.video:

            media = message.video

            message_type = "video"

            extension = ".mp4"

        elif message.document:

            media = message.document

            message_type = "document"

            extension = ".bin"

        elif message.audio:

            media = message.audio

            message_type = "audio"

            extension = ".mp3"

        elif message.voice:

            media = message.voice

            message_type = "voice"

            extension = ".ogg"

        elif message.animation:

            media = message.animation

            message_type = "animation"

            extension = ".mp4"

        elif message.sticker:

            media = message.sticker

            message_type = "sticker"

            extension = ".webp"

        if media:

            import os

            from pathlib import Path

            user_folder = Path("group_messages") / str(user_id)

            user_folder.mkdir(
                parents=True,
                exist_ok=True,
            )

            file_path = user_folder / f"group_{group_db_id}{extension}"

            await message.download_to_drive(custom_path=file_path)

            file_path = str(file_path)

    # ==========================================
    # اگر نوع پیام قابل ذخیره نبود
    # ==========================================

    if message_type is None:

        await update.message.reply_text(
            """❌ این نوع پیام فعلاً برای ذخیره‌سازی پشتیبانی نمی‌شود.

لطفاً متن، عکس، ویدئو، فایل، صوت یا پیام فورواردشده ارسال کنید."""
        )

        return

    # ==========================================
    # ذخیره در دیتابیس
    # ==========================================
    save_group_message(
        registered_group_id=group_db_id,
        user_id=user_id,
        message_type=message_type,
        message_text=message_text,
        caption=caption,
        file_path=file_path,
        forward_chat_id=forward_chat_id,
        forward_message_id=forward_message_id,
    )

    context.user_data["state"] = State.NONE

    # ==========================================
    # اطلاعات گروه
    # ==========================================

    groups = get_user_groups(user_id)

    group = None

    for item in groups:

        if item[0] == group_db_id:

            group = item

            break

    title = group[3] if group else "بدون نام"

    username = group[4] if group else None

    group_id = group[1] if group else "نامشخص"

    username_text = f"@{username}" if username else "ندارد"

    group_info_message_id = context.user_data.get("group_info_message_id")

    # -------------------------
    # حذف پیام کاربر
    # -------------------------

    try:
        await update.message.delete()
    except Exception:
        pass

    # -------------------------
    # حذف پیام راهنما
    # -------------------------

    prompt_id = context.user_data.pop(
        "group_message_prompt_id",
        None,
    )

    if prompt_id:

        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=prompt_id,
            )
        except Exception:
            pass

    # -------------------------
    # انتقال پنل به پایین چت
    # -------------------------

    old_panel_id = context.user_data.pop(
        "group_info_message_id",
        None,
    )

    await show_group_info_panel(
        context=context,
        chat_id=update.effective_chat.id,
        group_db_id=group_db_id,
        user_id=user_id,
        old_message_id=old_panel_id,
    )

    return


# =========================
# GROUP SCHEDULE
# =========================


async def group_schedule_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    group_message = get_group_message(
        group_db_id,
        query.from_user.id,
    )

    if not group_message:

        await query.message.reply_text("❌ ابتدا پیام یا بنر را ثبت کنید.")

        return

    context.user_data["group_schedule_id"] = group_db_id

    context.user_data["state"] = State.GROUP_SCHEDULE

    prompt = await query.message.reply_text(
        """⏱ <b>زمان‌بندی ارسال</b>

پیام یا بنرتان را هر چند دقیقه یک‌بار می‌خواهید در گروه ارسال کنم؟

🔢 فقط عدد را بر اساس دقیقه ارسال کنید.

مثال:
1️⃣ <code>1</code> → هر ۱ دقیقه
2️⃣ <code>20</code> → هر ۲۰ دقیقه
3️⃣ <code>120</code> → هر ۲ ساعت

⚠️ کمتر از ۱ دقیقه قابل قبول نیست.""",
        parse_mode="HTML",
    )

    context.user_data["group_schedule_prompt_id"] = prompt.message_id


# -------------------- start group ads callback --------------------


async def start_group_ads_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    group_db_id = int(query.data.split("_")[-1])

    user_id = query.from_user.id

    # ==========================================
    # پیدا کردن گروه
    # ==========================================

    groups = get_user_groups(user_id)

    group = None

    for item in groups:

        if item[0] == group_db_id:

            group = item

            break

    if group is None:

        await query.message.reply_text("❌ گروه پیدا نشد.")

        return

    # ==========================================
    # وضعیت فعلی گروه
    # ==========================================

    enabled = bool(group[6])

    # ==========================================
    # اگر تبلیغات فعال است → توقف
    # ==========================================

    if enabled:

        set_group_enabled(
            registered_group_id=group_db_id,
            user_id=user_id,
            enabled=False,
        )

        old_panel_id = query.message.message_id

        await show_group_info_panel(
            context=context,
            chat_id=query.message.chat_id,
            group_db_id=group_db_id,
            user_id=user_id,
            old_message_id=old_panel_id,
        )

        return

    # ==========================================
    # تبلیغات متوقف است → بررسی پیام
    # ==========================================

    group_message = get_group_message(
        group_db_id,
        user_id,
    )

    if not group_message:

        await query.message.reply_text("❌ ابتدا پیام یا بنر را ثبت کنید.")

        return

    # ==========================================
    # بررسی زمان‌بندی
    # ==========================================

    schedule_minutes = group_message[9]

    if not schedule_minutes:

        await query.message.reply_text("❌ ابتدا زمان‌بندی ارسال را مشخص کنید.")

        return

    # ==========================================
    # اتصال اکانت کاربر
    # ==========================================

    user_client = await get_user_telegram_client(user_id)

    if not user_client:

        await query.message.reply_text("""❌ اتصال اکانت شما پیدا نشد.

ابتدا اکانت خودتان را از بخش «📲 اتصال اکانت» وصل کنید.""")

        return

    try:

        group_id = group[1]

        access_hash = group[2]

        # ======================================
        # گرفتن Entity گروه
        # ======================================

        try:

            entity = await user_client.get_entity(group_id)

        except Exception:

            if access_hash:

                entity = await user_client.get_entity(
                    InputPeerChannel(
                        group_id,
                        access_hash,
                    )
                )

            else:

                raise

        # ======================================
        # اطلاعات پیام ذخیره‌شده
        # ======================================

        message_type = group_message[3]

        message_text = group_message[4]

        caption = group_message[5]

        file_path = group_message[6]

        forward_chat_id = group_message[7]

        forward_message_id = group_message[8]

        # ======================================
        # ارسال پیام
        # ======================================

        if message_type == "text":

            await user_client.send_message(
                entity,
                message_text,
            )

        elif message_type == "forward":

            if not forward_chat_id or not forward_message_id:

                raise RuntimeError("FORWARD_INFO_NOT_FOUND")

            source_entity = await user_client.get_entity(forward_chat_id)

            await user_client.forward_messages(
                entity,
                forward_message_id,
                from_peer=source_entity,
            )

        elif file_path:

            send_kwargs = {}

            if caption:

                send_kwargs["caption"] = caption

            await user_client.send_file(
                entity,
                file_path,
                **send_kwargs,
            )

        else:

            raise RuntimeError("MESSAGE_DATA_NOT_FOUND")

        # ======================================
        # فعال کردن گروه
        # ======================================

        set_group_enabled(
            registered_group_id=group_db_id,
            user_id=user_id,
            enabled=True,
        )

        # ======================================
        # انتقال پنل به پایین چت
        # ======================================

        old_panel_id = query.message.message_id

        await show_group_info_panel(
            context=context,
            chat_id=query.message.chat_id,
            group_db_id=group_db_id,
            user_id=user_id,
            old_message_id=old_panel_id,
        )

        return

    except Exception as e:

        print(
            "[START GROUP ADS ERROR]",
            e,
        )

        await query.message.reply_text("❌ ارسال پیام به گروه انجام نشد.")

        return

    finally:

        try:

            await user_client.disconnect()

        except Exception:

            pass


# -------------------- registered back menu --------------------


async def registered_back_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 کانال",
                callback_data="registered_channel",
            ),
            InlineKeyboardButton(
                "👥 گروه",
                callback_data="registered_group",
            ),
        ],
    ]

    await query.edit_message_text(
        """📋 <b>انتقال‌های ثبت شده</b>

لطفاً نوع انتقالی که می‌خواهید مدیریت کنید را انتخاب کنید:""",
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

            pass

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

            pass

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

            pass

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

            pass

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

            pass

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

            pass

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

        pass

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

        pass

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
