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
)

WAIT_GROUP = 100


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

        await query.message.reply_text("آیدی یا یوزرنیم گروه تبلیغاتی را ارسال کن.")

        return WAIT_GROUP

    elif query.data == "ads_groups":

        await ads_groups(
            update,
            context,
        )

        return ConversationHandler.END

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

        return ConversationHandler.END

    elif query.data.startswith("ads_group_"):

        await ads_group_info(
            update,
            context,
        )

        return ConversationHandler.END

    return ConversationHandler.END


# ---------------------- receive group --------------------


async def receive_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    group_input = update.message.text.strip()

    if not group_input:
        await update.message.reply_text("❌ یوزرنیم یا آیدی گروه را ارسال کنید.")
        return WAIT_GROUP

    # -----------------------------
    # فقط گروه عمومی
    # -----------------------------

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

    # -----------------------------
    # دریافت اطلاعات گروه
    # -----------------------------

    try:

        entity = await tg_client.get_entity(group_input)

    except Exception:

        await update.message.reply_text(
            "❌ گروه پیدا نشد.\n\n" "مطمئن شوید یوزرنیم گروه عمومی صحیح است."
        )

        return WAIT_GROUP

    # -----------------------------
    # بررسی گروه بودن
    # -----------------------------

    if not isinstance(entity, (Chat, Channel)):

        await update.message.reply_text("❌ این آدرس مربوط به یک گروه نیست.")

        return WAIT_GROUP

    # Channel می‌تواند کانال باشد
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

    # -----------------------------
    # اطلاعات گروه
    # -----------------------------

    telegram_group_id = entity.id

    title = getattr(
        entity,
        "title",
        None,
    )

    username = getattr(
        entity,
        "username",
        None,
    )

    if not username:

        await update.message.reply_text("❌ گروه باید عمومی باشد و یوزرنیم داشته باشد.")

        return WAIT_GROUP

    group_username = f"@{username}"

    # -----------------------------
    # جلوگیری از ثبت تکراری
    # -----------------------------

    existing_groups = get_advertising_groups(update.effective_user.id)

    for existing in existing_groups:

        if existing[3] == telegram_group_id:

            await update.message.reply_text("⚠️ این گروه قبلاً ثبت شده است.")

            return ConversationHandler.END

    # -----------------------------
    # ذخیره
    # -----------------------------

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
            type(e).name,
            str(e),
        )

        await update.message.reply_text("❌ ذخیره گروه انجام نشد.")

        return ConversationHandler.END

    await update.message.reply_text(f"""✅ گروه با موفقیت ثبت شد.

📢 نام گروه: {title or "نامشخص"}
🔗 یوزرنیم: {group_username}
🆔 شناسه: {telegram_group_id}""")

    return ConversationHandler.END


# ---------------------- ads groups --------------------


async def ads_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    groups = get_advertising_groups(
        query.from_user.id,
    )

    if not groups:

        await query.edit_message_text("❌ هنوز هیچ گروهی ثبت نشده است.")
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

    # ساختار جدول:
    # 0 id
    # 1 telegram_id
    # 2 group_username
    # 3 group_id
    # 4 title
    # 5 interval_minutes
    # 6 enabled
    # 7 message_type
    # 8 message_text
    # 9 forward_chat_id
    # 10 forward_message_id

    status = "🟢 فعال" if group[6] else "🔴 متوقف"

    keyboard = [
        [
            InlineKeyboardButton(
                "⏰ زمان‌بندی",
                callback_data=f"ads_time_{group_id}",
            )
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
                "📝 پیام",
                callback_data=f"ads_message_{group_id}",
            ),
            InlineKeyboardButton(
                "📨 فورواردی",
                callback_data=f"ads_forward_{group_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف گروه",
                callback_data=f"ads_delete_{group_id}",
            )
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

👥 گروه:
{group[4] or "نامشخص"}

🔗 یوزرنیم:
{group[2]}

🆔 شناسه:
{group[3]}

⏱ فاصله ارسال:
{group[5]} دقیقه

📊 وضعیت:
{status}""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
