from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from config import ADMIN_ID
from telegram.ext import ConversationHandler
from telethon.tl.types import Chat, Channel
from telegram_client import tg_client

from telegram.ext import ConversationHandler
from database import (
    add_advertising_group,
    get_advertising_groups,
    get_advertising_group,
    get_connection,
)

import asyncio

ads_tasks = {}

# ---------------------- start group sender --------------------


async def start_group_sender(application, group_id):

    if group_id in ads_tasks:

        task = ads_tasks[group_id]

        if not task.done():
            return

    async def worker():

        from database import (
            get_advertising_group,
        )

        while True:

            try:

                group = get_advertising_group(group_id)

                if not group:
                    break

                enabled = bool(group[6])

                if not enabled:
                    break

                interval = int(group[5])

                source_chat_id = group[11]
                source_message_id = group[12]

                target = group[2]

                if source_chat_id and source_message_id:

                    try:

                        await tg_client.forward_messages(
                            entity=target,
                            messages=source_message_id,
                            from_peer=source_chat_id,
                        )

                    except Exception:
                        pass

                await asyncio.sleep(interval * 60)

            except asyncio.CancelledError:
                break

            except Exception:

                await asyncio.sleep(10)

    ads_tasks[group_id] = asyncio.create_task(worker())


# ------------------------------------------

WAIT_GROUP = 100
WAIT_INTERVAL = 101
CURRENT_AD_GROUP = "CURRENT_AD_GROUP"

# ---------------------- ads panel --------------------


async def ads_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "➕ افزودن گروه تبلیغاتی",
                callback_data="ads_add_group",
            )
        ],
        [
            InlineKeyboardButton(
                "📋 گروه های ثبت شده",
                callback_data="ads_groups",
            )
        ],
    ]

    await update.message.reply_text(
        """📢 <b>پنل مدیریت تبلیغات</b>

به بخش مدیریت تبلیغات خوش آمدید.

از طریق دکمه‌های زیر می‌توانید گروه‌های تبلیغاتی خود را مدیریت کنید، گروه جدید اضافه کنید و تنظیمات تبلیغات را انجام دهید.

👇 <b>برای ادامه، یکی از گزینه‌های زیر را انتخاب کنید:</b>""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ---------------------- ads buttons --------------------


async def ads_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ads_add_group":
        context.user_data["ads_state"] = "WAIT_GROUP"

        await query.message.reply_text("آیدی یا یوزرنیم گروه تبلیغاتی را ارسال کن.")
        return

    elif query.data.startswith("ads_time_"):
        group_id = int(query.data.split("_")[2])

        context.user_data[CURRENT_AD_GROUP] = group_id
        context.user_data["ads_state"] = "WAIT_INTERVAL"

        await query.message.reply_text(
            "⏰ لطفاً تعداد دقیقه را ارسال کنید.\n\nمثال:\n60"
        )
        return

    elif query.data.startswith("ads_message_"):
        group_id = int(query.data.split("_")[2])

        context.user_data[CURRENT_AD_GROUP] = group_id
        context.user_data["ads_state"] = "WAIT_MESSAGE"

        await query.message.reply_text(
            "📨 پیام تبلیغاتی را ارسال کنید.\n\n"
            "می‌توانید متن، عکس، ویدیو یا هر پیامی را ارسال کنید."
        )
        return

    elif query.data == "ads_groups":
        await ads_groups(update, context)
        return

    elif query.data == "ads_back":
        keyboard = [
            [
                InlineKeyboardButton(
                    "➕ افزودن گروه تبلیغاتی",
                    callback_data="ads_add_group",
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 گروه های ثبت شده",
                    callback_data="ads_groups",
                )
            ],
        ]

        await query.edit_message_text(
            """📢 <b>پنل مدیریت تبلیغات</b>

به بخش مدیریت تبلیغات خوش آمدید.

از طریق دکمه‌های زیر می‌توانید گروه‌های تبلیغاتی خود را مدیریت کنید، گروه جدید اضافه کنید و تنظیمات تبلیغات را انجام دهید.

👇 <b>برای ادامه، یکی از گزینه‌های زیر را انتخاب کنید:</b>""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    elif query.data.startswith("ads_toggle_"):

        from database import (
            get_advertising_group,
            set_advertising_group_enabled,
        )

        group_id = int(query.data.split("_")[2])

        group = get_advertising_group(group_id)

        if not group:
            return

        enabled = not bool(group[6])

        set_advertising_group_enabled(
            group_id,
            enabled,
        )

        if enabled:
            await start_group_sender(
                context.application,
                group_id,
            )

        group = get_advertising_group(group_id)

        status = "🟢 فعال" if group[6] else "🔴 متوقف"

        keyboard = [
            [
                InlineKeyboardButton(
                    "⏰ زمان‌بندی",
                    callback_data=f"ads_time_{group_id}",
                ),
                InlineKeyboardButton(
                    "📝 پیام",
                    callback_data=f"ads_message_{group_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "⏹ توقف انتقال" if group[6] else "▶️ شروع انتقال",
                    callback_data=f"ads_toggle_{group_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📨 فورواردی",
                    callback_data=f"ads_forward_{group_id}",
                ),
                InlineKeyboardButton(
                    "🗑 حذف گروه",
                    callback_data=f"ads_delete_{group_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="ads_groups",
                )
            ],
        ]

        await query.edit_message_text(
            f"""📢 <b>اطلاعات گروه تبلیغاتی</b>

👥 گروه: {group[4] or "نامشخص"}
🔗 یوزرنیم: {group[2]}
🆔 شناسه: {group[3]}
⏱ فاصله ارسال: {group[5]} دقیقه
📊 وضعیت: {status}""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )

        return

    elif query.data.startswith("ads_group_"):
        await ads_group_info(update, context)
        return


# ---------------------- receive group --------------------


async def receive_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    # اگر کاربر دستور یا یکی از دکمه‌های کیبورد را زد،
    # از حالت افزودن گروه خارج شو.
    text = (update.message.text or "").strip()

    if text.startswith("/"):
        return ConversationHandler.END

    MAIN_KEYBOARD = {
        "🏠 خانه",
        "➕ اتصال کانال‌ها",
        "📋 کانال‌های ثبت شده",
        "👤 حساب کاربری",
        "💬 پشتیبانی",
    }

    if text in MAIN_KEYBOARD:
        return ConversationHandler.END

    group_input = text

    if not group_input:
        await update.message.reply_text("❌ یوزرنیم یا آیدی گروه را ارسال کنید.")
        return WAIT_GROUP

    if group_input.startswith("https://t.me/"):
        group_input = group_input.replace(
            "https://t.me/",
            "",
            1,
        )

    elif group_input.startswith("http://t.me/"):
        group_input = group_input.replace(
            "http://t.me/",
            "",
            1,
        )

    if not group_input.startswith("@"):
        group_input = "@" + group_input

    try:

        entity = await tg_client.get_entity(group_input)

    except Exception:

        await update.message.reply_text(
            "❌ گروه پیدا نشد.\n\n" "مطمئن شوید یوزرنیم گروه عمومی صحیح است."
        )

        return WAIT_GROUP

    if not isinstance(entity, (Chat, Channel)):

        await update.message.reply_text("❌ این آدرس مربوط به یک گروه نیست.")

        return WAIT_GROUP

    if isinstance(entity, Channel):

        if getattr(entity, "broadcast", False):

            await update.message.reply_text(
                "❌ این یک کانال است.\n\n"
                "لطفاً فقط یوزرنیم یک گروه عمومی را ارسال کنید."
            )

            return WAIT_GROUP

        if not getattr(entity, "megagroup", False):

            await update.message.reply_text("❌ این مورد یک گروه عمومی معتبر نیست.")

            return WAIT_GROUP

    telegram_group_id = entity.id

    title = getattr(entity, "title", None)
    username = getattr(entity, "username", None)

    if not username:

        await update.message.reply_text("❌ گروه باید عمومی باشد و یوزرنیم داشته باشد.")

        return WAIT_GROUP

    group_username = f"@{username}"

    existing_groups = get_advertising_groups(
        update.effective_user.id,
    )

    for existing in existing_groups:

        if existing[3] == telegram_group_id:

            await update.message.reply_text("⚠️ این گروه قبلاً ثبت شده است.")

            return ConversationHandler.END

    try:

        add_advertising_group(
            telegram_id=update.effective_user.id,
            group_username=group_username,
            group_id=telegram_group_id,
            title=title,
        )

    except Exception as e:

        print(
            "ADD ADVERTISING GROUP ERROR:",
            type(e).__name__,
            str(e),
        )

        await update.message.reply_text("❌ ذخیره گروه انجام نشد.")

        return ConversationHandler.END

    await update.message.reply_text(f"""✅ گروه با موفقیت ثبت شد.

📢 نام گروه: {title or "نامشخص"}
🔗 یوزرنیم: {group_username}
🆔 شناسه: {telegram_group_id}""")

    context.user_data.pop("ads_state", None)
    return ConversationHandler.END


# ---------------------- ads groups --------------------


async def ads_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    groups = get_advertising_groups(
        query.from_user.id,
    )

    if not groups:

        await query.message.reply_text("❌ هنوز هیچ گروهی ثبت نشده است.")
        return

    keyboard = []

    for group in groups:

        keyboard.append(
            [
                InlineKeyboardButton(
                    group[2],
                    callback_data=f"ads_group_{group[0]}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="ads_back",
            )
        ]
    )

    await query.edit_message_text(
        """📋 <b>گروه‌های ثبت‌شده شما</b>

برای مشاهده اطلاعات و تنظیمات هر گروه، روی گروه موردنظر از لیست زیر کلیک کنید.""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ---------------------- ads group info --------------------


async def ads_group_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    group_id = int(query.data.split("_")[2])

    group = get_advertising_group(group_id)

    if not group:
        await query.edit_message_text("❌ گروه پیدا نشد.")
        return

    status = "🟢 فعال" if group[6] else "🔴 متوقف"

    keyboard = [
        [
            InlineKeyboardButton(
                "⏰ زمان‌بندی",
                callback_data=f"ads_time_{group_id}",
            ),
            InlineKeyboardButton(
                "📝 پیام",
                callback_data=f"ads_message_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "⏹ توقف انتقال" if group[6] else "▶️ شروع انتقال",
                callback_data=f"ads_toggle_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "📨 فورواردی",
                callback_data=f"ads_forward_{group_id}",
            ),
            InlineKeyboardButton(
                "🗑 حذف گروه",
                callback_data=f"ads_delete_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="ads_groups",
            )
        ],
    ]

    await query.edit_message_text(
        f"""📢 <b>اطلاعات گروه تبلیغاتی</b>

👥 گروه: {group[4] or "نامشخص"}
🔗 یوزرنیم: {group[2]}
🆔 شناسه: {group[3]}
⏱ فاصله ارسال: {group[5]} دقیقه
📊 وضعیت: {status}""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ---------------------- ads message --------------------


async def ads_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.split("_")[2])

    context.user_data[CURRENT_AD_GROUP] = group_id
    context.user_data["ads_state"] = "WAIT_MESSAGE"

    await query.edit_message_text(
        "📨 پیام تبلیغاتی را ارسال کنید.\n\n"
        "می‌توانید متن، عکس، ویدیو، گیف، فایل یا هر نوع پیام تلگرامی را ارسال کنید."
    )


# ---------------------- receive interval --------------------


async def receive_interval(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    text = (update.message.text or "").strip()

    if not text.isdigit():

        await update.message.reply_text("❌ فقط عدد ارسال کنید.")

        return WAIT_INTERVAL

    minutes = int(text)

    if minutes < 1:

        await update.message.reply_text("❌ حداقل مقدار 1 دقیقه است.")

        return WAIT_INTERVAL

    group_id = context.user_data.get(CURRENT_AD_GROUP)

    if group_id is None:
        return ConversationHandler.END

    from database import update_ad_interval

    update_ad_interval(
        group_id,
        minutes,
    )

    await update.message.reply_text("✅ زمان‌بندی ذخیره شد.")

    group = get_advertising_group(group_id)

    status = "🟢 فعال" if group[6] else "🔴 متوقف"

    keyboard = [
        [
            InlineKeyboardButton(
                "⏰ زمان‌بندی",
                callback_data=f"ads_time_{group_id}",
            ),
            InlineKeyboardButton(
                "📝 پیام",
                callback_data=f"ads_message_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "▶️ شروع تبلیغات",
                callback_data=f"ads_start_{group_id}",
            ),
            InlineKeyboardButton(
                "🛑 توقف",
                callback_data=f"ads_stop_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "📨 فورواردی",
                callback_data=f"ads_forward_{group_id}",
            ),
            InlineKeyboardButton(
                "🗑 حذف گروه",
                callback_data=f"ads_delete_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="ads_groups",
            )
        ],
    ]

    await update.message.reply_text(
        f"""📢 <b>اطلاعات گروه تبلیغاتی</b>

👥 گروه: {group[4] or "نامشخص"}
🔗 یوزرنیم: {group[2]}
🆔 شناسه: {group[3]}
⏱ فاصله ارسال: {group[5]} دقیقه
📊 وضعیت: {status}""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )

    context.user_data.pop(
        CURRENT_AD_GROUP,
        None,
    )

    return ConversationHandler.END


# ---------------------- receive ads message --------------------


async def receive_ads_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("ads_state") != "WAIT_MESSAGE":
        return

    group_id = context.user_data.get(CURRENT_AD_GROUP)

    if not group_id:
        return

    message = update.effective_message

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE advertising_groups
        SET 
            message_type = ?,
            forward_chat_id = ?,
            forward_message_id = ?
        WHERE id = ?
        """,
        (
            "forward",
            message.chat_id,
            message.message_id,
            group_id,
        ),
    )

    conn.commit()
    conn.close()

    context.user_data.pop(
        "ads_state",
        None,
    )

    context.user_data.pop(
        CURRENT_AD_GROUP,
        None,
    )

    await message.reply_text("✅ پیام تبلیغاتی ذخیره شد.")
