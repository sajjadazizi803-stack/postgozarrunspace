from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ApplicationHandlerStop,
)

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
)

from handlers.connect_account import (
    connect_account,
    receive_source_channel,
    receive_target_channel,
    finish_transfer,
    start_group_registration,
    receive_group,
    group_message_callback,
    group_schedule_callback,
    receive_group_message,
    delete_group_callback,
    confirm_delete_group_callback,
    cancel_delete_group_callback,
    start_group_ads_callback,
)

from handlers.connect_account import (
    delete_transfer_callback,
    toggle_transfer_callback,
    back_to_registered_channels,
    registered_channels_list,
    registered_groups_list,
    registered_channels_from_keyboard,
    registered_groups_from_keyboard,
    registered_group_info,
    registered_back_menu,
    transfer_settings,
    remove_lines_setting,
)

from handlers.support import (
    forward_to_admin,
    admin_reply,
    contact_support_callback,
)

from handlers.connect_account import (
    change_source_callback,
    confirm_source_callback,
    cancel_source_callback,
)

import config
from telegram_client import tg_client
from handlers.connect_account import registered_channels
from handlers.connect_account import transfer_info
from database import set_remove_last_lines
from handlers.connect_account import append_lines_setting
from database import set_append_last_lines
from config import ADMIN_ID
from telegram import KeyboardButton, ReplyKeyboardMarkup
from conversation import State
from pathlib import Path
from database import save_api_id
from database import save_api_hash
from database import save_phone
from database import get_account
from telethon.errors import SessionPasswordNeededError
from telethon.errors import PasswordHashInvalidError
import asyncio
from database import get_admin_statistics

CHANNEL_USERNAME = "@SADSSCS"

from handlers.connect_account import (
    change_target_callback,
    confirm_target_callback,
    cancel_target_callback,
    finish_change_target,
)

# ---------------------- add menu --------------------

ADD_MENU = ReplyKeyboardMarkup(
    [
        [
            "📢 کانال",
            "👥 گروه",
        ],
        [
            "🔙",
        ],
    ],
    resize_keyboard=True,
)

# ---------------------- clear waiting state --------------------


def clear_waiting_state(context):

    context.user_data["state"] = State.NONE

    context.user_data.pop("source_channel", None)
    context.user_data.pop("target_channel", None)

    context.user_data.pop("pending_source", None)
    context.user_data.pop("pending_target", None)

    context.user_data.pop("changing_source", None)
    context.user_data.pop("changing_target", None)

    context.user_data.pop("change_source_transfer_id", None)
    context.user_data.pop("change_target_transfer_id", None)

    context.user_data.pop("remove_lines_transfer_id", None)
    context.user_data.pop("append_lines_transfer_id", None)

    context.user_data.pop("group_message_group_id", None)
    context.user_data.pop("group_schedule_id", None)

    context.user_data.pop("group_info_message_id", None)
    context.user_data.pop("group_message_prompt_id", None)
    context.user_data.pop("group_schedule_prompt_id", None)

    context.user_data.pop("conversation", None)
    context.user_data.pop("wait_group", None)

    # اطلاعات ورود اکانت
    context.user_data.pop("login_phone", None)
    context.user_data.pop("phone_code_hash", None)


# ---------------------- training keyboard --------------------


def training_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚠️ نکات مهم",
                    callback_data="training_rules",
                ),
                InlineKeyboardButton(
                    "📢 اتصال کانال‌ها",
                    callback_data="training_connect",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✂️ حذف خطوط آخر",
                    callback_data="training_delete_lines",
                ),
                InlineKeyboardButton(
                    "✍️ افزودن خطوط آخر",
                    callback_data="training_add_lines",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔐 اتصال اکانت",
                    callback_data="training_account",
                ),
            ],
        ]
    )


# ---------------------- show training menu --------------------


async def show_training_menu(update, context):

    text = (
        "📚 <b>آموزش استفاده از ربات</b>\n\n"
        "برای مشاهده آموزش هر بخش، روی دکمه مورد نظر کلیک کنید.\n\n"
        "پیشنهاد می‌شود تمام بخش‌ها را با دقت مطالعه کنید "
        "تا بتوانید بهتر از ربات استفاده کنید. ✅"
    )

    await update.message.reply_text(
        text, reply_markup=training_keyboard(), parse_mode="HTML"
    )


# ---------------------- check join --------------------


async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    member = await context.bot.get_chat_member(
        CHANNEL_USERNAME,
        query.from_user.id,
    )

    if member.status in (
        "member",
        "administrator",
        "creator",
    ):

        keyboard = ReplyKeyboardMarkup(
            [
                [
                    "➕ افزودن انتقال",
                    "📋 انتقال‌های ثبت شده",
                ],
                [
                    "📚 آموزش استفاده",
                    "📲 اتصال اکانت",
                ],
                [
                    "💬 ارتباط با پشتیبانی",
                ],
            ],
            resize_keyboard=True,
        )

        await query.message.edit_text(
            f"""👋 <b>سلام {query.from_user.first_name}، به ربات RunSpace خوش اومدی 🚀</b>

⚠️ <b>قبل از استفاده، حتماً بخش آموزش رو بخون</b>""",
            parse_mode="HTML",
        )

        await query.message.reply_text(
            "به منوی اصلی بازگشتید 👇",
            reply_markup=keyboard,
        )

    else:

        await query.answer(
            "❌ هنوز عضو کانال نشدی.",
            show_alert=True,
        )


# ------------------ admin panel ---------------------


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    # فقط ادمین اصلی
    if user_id != ADMIN_ID:

        return

    stats = get_admin_statistics()

    text = (
        "👑 <b>پنل مدیریت RunSpace</b>\n\n"
        "📊 <b>آمار ربات</b>\n\n"
        f"👥 تعداد کاربران: <b>{stats['users']}</b>\n"
        f"🔐 اکانت‌های متصل: <b>{stats['accounts']}</b>\n"
        f"📢 انتقال‌های کانال: <b>{stats['transfers']}</b>\n"
        f"📣 گروه‌های تبلیغاتی: <b>{stats['groups']}</b>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )

    return


# =========================
# START
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    first_name = update.effective_user.first_name or "دوست عزیز"

    try:

        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=update.effective_user.id,
        )

        if member.status in (
            "member",
            "administrator",
            "creator",
        ):

            keyboard = ReplyKeyboardMarkup(
                [
                    [
                        "➕ افزودن انتقال",
                        "📋 انتقال‌های ثبت شده",
                    ],
                    [
                        "📚 آموزش استفاده",
                        "📲 اتصال اکانت",
                    ],
                    [
                        "💬 ارتباط با پشتیبانی",
                    ],
                ],
                resize_keyboard=True,
            )

            if not context.user_data.get("started"):

                context.user_data["started"] = True

                await update.message.reply_text(
                    f"""👋 <b>سلام {first_name}، به ربات RunSpace خوش اومدی 🚀</b>

⚠️ <b>قبل از استفاده، حتماً بخش آموزش رو بخون</b>""",
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )

            else:

                await update.message.reply_text(
                    "✅ <b>به منوی اصلی بازگشتید.</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )

            return

    except Exception:
        pass

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 عضویت در کانال",
                    url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}",
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ ورود به ربات",
                    callback_data="check_join",
                )
            ],
        ]
    )

    await update.message.reply_text(
        f"""👋 <b>سلام {first_name}، به RunSpace خوش اومدی.</b>

⚠️ <b>قبل از استفاده از ربات باید در کانال زیر عضو بشی.</b>""",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# =========================
# BUTTONS
# =========================


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "connect_account":

        await connect_account(
            update,
            context,
        )

        return

    if query.data == "training_account":

        await training_account(
            update,
            context,
        )

        return

    if query.data == "training_back":

        try:
            await query.message.delete()
        except Exception:
            pass

        text = (
            "📚 <b>آموزش استفاده از ربات</b>\n\n"
            "برای مشاهده آموزش هر بخش، روی دکمه مورد نظر کلیک کنید.\n\n"
            "پیشنهاد می‌شود تمام بخش‌ها را با دقت مطالعه کنید "
            "تا بتوانید بهتر از ربات استفاده کنید. ✅"
        )

        await query.message.chat.send_message(
            text,
            reply_markup=training_keyboard(),
            parse_mode="HTML",
        )

        return

    if query.data == "training_rules":

        await training_rules(
            update,
            context,
        )

        return

    if query.data == "training_connect":

        await training_connect(
            update,
            context,
        )

        return

    if query.data == "training_delete_lines":

        await training_delete_lines(
            update,
            context,
        )

        return

    if query.data == "training_add_lines":

        await training_add_lines(
            update,
            context,
        )

        return


# --------------------- training rules -------------------


async def training_rules(update, context):

    query = update.callback_query

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        "<b>⚠️ نکات مهم قبل از اتصال کانال‌ها</b>\n\n"
        "• بعد از اینکه کانال مبدا و مقصد رو به ربات دادی، حتماً باید اکانت <b>@egpora_e3</b> داخل <b>کانال مقصد</b> ادمین باشه.\n\n"
        "• ربات <b>@Runspace_S_bot</b> هم باید داخل <b>کانال مقصد</b> ادمین باشه و اجازه ارسال پیام داشته باشه.\n\n"
        "• کانال مبدا و کانال مقصد <b>حتماً باید عمومی (Public)</b> باشن.\n\n"
        "• این ربات فقط برای <b>انتقال بین کانال‌ها</b> ساخته شده و از <b>گروه‌ها پشتیبانی نمی‌کنه.</b>\n\n"
        "• اکانت و ربات <b>فقط در کانال مقصد</b> باید ادمین باشن و در کانال مبدا نیازی به ادمین بودن نیست.\n\n"
        "• بعد از اینکه کانال مبدا و مقصد رو ثبت کردی و اکانت و ربات رو ادمین کردی، روی دکمه <b>«✅ انجام شد»</b> بزن.\n\n"
        "• هر کاربر فقط <b>یک انتقال</b> می‌تونه ثبت کنه. اگر بعداً خواستی مبدا یا مقصد رو تغییر بدی، از قسمت <b>«📋 انتقال‌های ثبت شده»</b> این کار رو انجام بده و دوباره انتقال جدید نساز.\n\n"
        "❗ اگر مراحل بالا رو درست انجام ندی، انتقال ثبت نمیشه یا پیام‌ها منتقل نخواهند شد.\n\n"
        "• بعد از ثبت انتقال، از قسمت <b>«📋 انتقال‌های ثبت شده»</b> می‌تونی انتقالت رو مدیریت کنی، مبدا یا مقصد رو تغییر بدی، انتقال رو متوقف یا فعال کنی و تنظیماتش رو تغییر بدی.\n\n"
        "💬 اگر هنگام استفاده از ربات با مشکلی روبه‌رو شدی یا پیشنهادی داشتی، خوشحال میشیم از قسمت <b>«پشتیبانی»</b> با ما در میون بذاری.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به آموزش",
                        callback_data="training_back",
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    return


# --------------------- training connect -------------------


async def training_connect(update, context):

    query = update.callback_query

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        "<b>📢 اتصال کانال‌ها</b>\n\n"
        "برای شروع کار با ربات، ابتدا از منوی اصلی روی گزینه:\n\n"
        "➕ <b>افزودن کانال</b>\n\n"
        "کلیک کنید.\n\n"
        "سپس اطلاعات کانال‌ها را برای ربات ارسال کنید:\n\n"
        "📌 <b>کانال مبدا:</b>\n"
        "کانالی که می‌خواهید پست‌ها از آن دریافت شود.\n\n"
        "📌 <b>کانال مقصد:</b>\n"
        "کانالی که می‌خواهید پست‌ها در آن ارسال شود.\n\n"
        "بعد از اتصال، ربات پست‌های جدید کانال مبدا را دریافت کرده "
        "و در کانال مقصد ارسال می‌کند. ✅",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به آموزش",
                        callback_data="training_back",
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    return


# --------------------- training delete lines -------------------


async def training_delete_lines(update, context):

    query = update.callback_query

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        "<b>✂️ حذف خطوط آخر</b>\n\n"
        "با این قابلیت می‌توانید چند خط آخر پست‌های کانال مبدا را حذف کنید.\n\n"
        "مثلاً اگر آخر همه پست‌ها تبلیغ، آیدی کانال یا متن اضافه وجود دارد، "
        "می‌توانید به ربات بگویید آن‌ها را حذف کند.\n\n"
        "<b>مثال:</b>\n"
        "اگر مقدار <code>3</code> را تنظیم کنید، ربات قبل از ارسال، "
        "<b>۳ خط آخر</b> متن پست را حذف می‌کند و سپس آن را در کانال مقصد ارسال می‌کند.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به آموزش",
                        callback_data="training_back",
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    return


# --------------------- training add lines -------------------


async def training_add_lines(update, context):

    query = update.callback_query

    try:
        await query.message.delete()
    except Exception:
        pass

    await query.message.chat.send_message(
        "<b>✍️ افزودن خطوط آخر</b>\n\n"
        "با این قابلیت می‌توانید یک متن ثابت به انتهای تمام پست‌های ارسالی اضافه کنید.\n\n"
        "برای مثال می‌توانید:\n\n"
        "• آیدی کانال خودتان\n"
        "• متن تبلیغاتی\n"
        "• امضا\n"
        "• لینک دلخواه\n\n"
        "را ثبت کنید تا ربات آن را به انتهای تمام پست‌های جدید اضافه کند.\n\n"
        "هر زمان هم بخواهید، می‌توانید متن ثبت‌شده را تغییر دهید.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت به آموزش",
                        callback_data="training_back",
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )

    return


# --------------------- training account -------------------


async def training_account(update, context):

    query = update.callback_query

    try:
        await query.message.delete()
    except Exception:
        pass

    photo_path = Path("images/training_account_connect.jpg")

    caption = (
        "🔐 <b>اتصال اکانت به ربات</b>\n\n"
        "<i>برای اتصال اکانت به ربات، حداقل به دو اکانت تلگرام نیاز دارید:</i>\n"
        "👤 <b>اکانت اول:</b> اکانتی که می‌خواهید به ربات وصل شود.\n"
        "👤 <b>اکانت دوم:</b> اکانتی که با آن داخل ربات کار می‌کنید.\n\n"
        "<i>با اکانتی که قرار است به ربات وصل شود، وارد "
        '<a href="https://my.telegram.org">my.telegram.org</a> '
        "شوید و <b>API ID</b> و <b>API HASH</b> را دریافت کنید.</i>\n\n"
        "<i>سپس <b>API ID</b> و <b>API HASH</b> و اطلاعاتی که ربات درخواست می‌کند "
        "را از طریق <b>اکانت دوم</b> برای ربات بفرستید.</i>\n\n"
        "📩 <b>وقتی ربات کد ورود خواست،</b> کدی را که برای "
        "<b>اکانت اول</b> ارسال شده، با اکانت اصلی برای ربات بفرستید.\n\n"
        "⚠️ <b>نکته مهم:</b> تمام مراحل را با یک اکانت انجام ندهید؛ "
        "<i>در این حالت ممکن است تلگرام اجازه اتصال اکانت را ندهد.</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 بازگشت به آموزش", callback_data="training_back")]]
    )

    if not photo_path.exists():

        await query.message.chat.send_message(
            caption,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        return

    with open(photo_path, "rb") as photo:

        await query.message.chat.send_photo(
            photo=photo,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    return


# =========================
# text buttons
# =========================
from conversation import State


async def text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user is None:
        return

    if update.message is None:
        return

    user_data = context.user_data

    # ==========================================
    # اگر پیام متنی نیست، فقط برای دکمه‌های متنی
    # چیزی انجام نده
    # ==========================================

    if update.message.text is None:

        if user_data.get("state") == State.GROUP_MESSAGE:
            return

        return

    text = update.message.text.strip()

    # =====================================================
    # تمام دکمه‌های اصلی ربات
    # =====================================================

    MAIN_BUTTONS = {
        "➕ افزودن انتقال",
        "📋 انتقال‌های ثبت شده",
        "📚 آموزش استفاده",
        "📲 اتصال اکانت",
        "💬 ارتباط با پشتیبانی",
        "📢 کانال",
        "👥 گروه",
        "👤 با اکانت خودم",
        "🤖 با اکانت ربات",
        "🏠",
        "🏠 خانه",
        "🔙",
    }

    # =====================================================
    # اگر کاربر دکمه‌ای زده، انتظار قبلی را لغو کن
    # =====================================================

    if text in MAIN_BUTTONS:

        clear_waiting_state(context)

        user_data["state"] = State.NONE

    # =====================================================
    # state جدید را بعد از لغو state قبلی بخوان
    # =====================================================

    state = user_data.get(
        "state",
        State.NONE,
    )

    # =========================
    # دریافت گروه
    # =========================

    if state == State.GROUP:

        await receive_group(
            update,
            context,
        )

        raise ApplicationHandlerStop

    # =========================
    # دریافت کانال مبدا
    # =========================

    if state == State.SOURCE_CHANNEL:

        await receive_source_channel(update, context)

        raise ApplicationHandlerStop

    # =========================
    # حذف خطوط آخر
    # =========================

    if state == State.REMOVE_LAST_LINES:

        try:

            count = int(update.message.text.strip())

        except:

            await update.message.reply_text("❌ لطفاً فقط عدد ارسال کن.\nمثال: 8")

            return

        transfer_id = context.user_data.get("remove_lines_transfer_id")

        if transfer_id:

            set_remove_last_lines(
                transfer_id,
                count,
            )

        context.user_data["state"] = State.NONE

        await update.message.reply_text(
            f"✅ تنظیم شد.\nاز این به بعد {count} خط آخر حذف میشه."
        )

        return

    # =========================
    # افزودن خطوط آخر
    # =========================

    if state == State.APPEND_LAST_LINES:

        transfer_id = context.user_data.get("append_lines_transfer_id")

        if not transfer_id:

            context.user_data["state"] = State.NONE

            return

        append_text = update.message.text.strip()

        set_append_last_lines(
            transfer_id,
            append_text,
        )

        context.user_data["state"] = State.NONE

        await update.message.reply_text("✅ متن ذخیره شد.")

        return

    # =========================
    # ارتباط با پشتیبانی
    # =========================

    if state == State.SUPPORT:

        await forward_to_admin(update, context)

        return

    # =========================
    # دریافت کانال مقصد
    # =========================

    if state == State.TARGET_CHANNEL:

        await receive_target_channel(update, context)

        raise ApplicationHandlerStop

    # =========================
    # انتخاب نوع افزودن
    # =========================

    if text == "➕ افزودن انتقال":

        context.user_data["transfer_menu"] = "TYPE"

        keyboard = ReplyKeyboardMarkup(
            [
                ["📢 کانال", "👥 گروه"],
                ["🔙"],
            ],
            resize_keyboard=True,
        )

        await update.message.reply_text(
            "نوع انتقال را انتخاب کنید:",
            reply_markup=keyboard,
        )

        return

    if text == "📢 کانال" and context.user_data.get("transfer_menu") == "REGISTERED":

        await registered_channels_from_keyboard(
            update,
            context,
        )

        return

    if text == "👥 گروه" and context.user_data.get("transfer_menu") == "REGISTERED":

        await registered_groups_from_keyboard(
            update,
            context,
        )

        return

    if text == "📢 کانال":

        context.user_data["transfer_menu"] = "ACCOUNT"

        keyboard = ReplyKeyboardMarkup(
            [
                ["👤 با اکانت خودم", "🤖 با اکانت ربات"],
                ["🏠", "🔙"],
            ],
            resize_keyboard=True,
        )

        await update.message.reply_text(
            "روش انتقال را انتخاب کنید:",
            reply_markup=keyboard,
        )

        return

    if text == "👤 با اکانت خودم":

        context.user_data["transfer_account_type"] = "user"

        await connect_account(update, context)

        return

    if text == "🤖 با اکانت ربات":

        context.user_data["transfer_account_type"] = "bot"
        context.user_data["account_type"] = "bot"
        context.user_data["client_type"] = "bot"
        context.user_data["use_bot_session"] = True

        await connect_account(
            update,
            context,
        )

        return

    if text == "🏠":

        keyboard = ReplyKeyboardMarkup(
            [
                [
                    "➕ افزودن انتقال",
                    "📋 انتقال‌های ثبت شده",
                ],
                [
                    "📚 آموزش استفاده",
                    "📲 اتصال اکانت",
                ],
                [
                    "💬 ارتباط با پشتیبانی",
                ],
            ],
            resize_keyboard=True,
        )

        await update.message.reply_text(
            "✅ به منوی اصلی بازگشتید.",
            reply_markup=keyboard,
        )

        return

    if text == "👥 گروه":

        context.user_data["transfer_menu"] = "GROUP"

        context.user_data["state"] = State.NONE

        await start_group_registration(
            update,
            context,
        )

        return

    if text == "🔙":

        menu = context.user_data.get("transfer_menu")

        if menu == "ACCOUNT":

            context.user_data["transfer_menu"] = "TYPE"

            keyboard = ReplyKeyboardMarkup(
                [
                    ["📢 کانال", "👥 گروه"],
                    ["🔙"],
                ],
                resize_keyboard=True,
            )

            await update.message.reply_text(
                "نوع انتقال را انتخاب کنید:",
                reply_markup=keyboard,
            )

            return

        keyboard = ReplyKeyboardMarkup(
            [
                [
                    "➕ افزودن انتقال",
                    "📋 انتقال‌های ثبت شده",
                ],
                [
                    "📚 آموزش استفاده",
                    "📲 اتصال اکانت",
                ],
                [
                    "💬 ارتباط با پشتیبانی",
                ],
            ],
            resize_keyboard=True,
        )

        context.user_data.pop("transfer_menu", None)

        await update.message.reply_text(
            "✅ <b>به منوی اصلی بازگشتید.</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        return

    # =========================
    # دکمه‌های اصلی
    # =========================

    if text == "📋 انتقال‌های ثبت شده":

        await registered_channels(update, context)

        return

    if text == "📚 آموزش استفاده":

        await show_training_menu(update, context)

        return

    if text == "📲 اتصال اکانت":

        try:

            image_path = Path(__file__).resolve().parent / "images" / "api_tutorial.jpg"

            with open(image_path, "rb") as photo:

                await update.message.reply_photo(
                    photo=photo,
                    caption="""🔐 اتصال اکانت

⚠️ حتما ابتدا بخش نکات مهم رو از قسمت آموزش استفاده مطالعه کنید.

حالا مراحل زیر رو انجام بدید:

1️⃣ وارد my.telegram.org بشید و شماره تلگرامتون رو وارد کنید
2️⃣ کدی که تلگرام برای اکانتتون ارسال می‌کنه رو وارد کنید.
3️⃣ روی API Development Tools بزنید و سپس Create Application رو انتخاب کنید.
4️⃣ بعد از ساخت برنامه، API ID و API HASH بهتون نمایش داده میشه و هر دو رو کپی کنید
طبق تصویر هر جا نیاز به وارد کردن نام و توضیحاتی بودید حتما باید انگلیسی باشه.

📩 حالا فقط API ID رو همینجا برام ارسال کنید تا بریم مرحله بعد. 🚀""",
                )

        except Exception as e:

            pass

            await update.message.reply_text(str(e))

        context.user_data["state"] = "WAIT_API_ID"

        raise ApplicationHandlerStop

    if text == "💬 ارتباط با پشتیبانی":

        await contact_support_callback(
            update,
            context,
        )

        return


# =========================
# conversation router
# =========================

from handlers.connect_account import (
    connect_account,
    receive_source_channel,
    receive_target_channel,
)


async def conversation_router(update, context):

    if update.message is None:
        return

    user_data = context.user_data or {}

    state = user_data.get(
        "state",
        State.NONE,
    )

    # ==========================================
    # دریافت پیام / بنر گروه
    # ==========================================

    if state == State.GROUP_MESSAGE:

        from handlers.connect_account import (
            receive_group_message,
        )

        # ==========================================
        # دریافت آلبوم
        # ==========================================

        media_group_id = getattr(
            update.message,
            "media_group_id",
            None,
        )

        if media_group_id:

            album_key = (
                f"group_album_" f"{update.effective_user.id}_" f"{media_group_id}"
            )

            album_messages = context.user_data.setdefault(
                album_key,
                [],
            )

            album_messages.append(update)

            # اولین پیام آلبوم یک Worker کوچک ایجاد می‌کند.
            # پیام‌های بعدی قبل از اجرای آن به لیست اضافه می‌شوند.

            task_key = f"{album_key}_task"

            if task_key not in context.user_data:

                async def process_album():

                    await asyncio.sleep(1.5)

                    updates = context.user_data.pop(
                        album_key,
                        [],
                    )

                    context.user_data.pop(
                        task_key,
                        None,
                    )

                    if not updates:
                        return

                    await receive_group_message(
                        updates[0],
                        context,
                        album_updates=updates,
                    )

                context.user_data[task_key] = asyncio.create_task(process_album())

            return

        return await receive_group_message(
            update,
            context,
        )

    # ==========================================
    # دریافت زمان‌بندی گروه
    # ==========================================

    if state == State.GROUP_SCHEDULE:

        if not update.message.text:

            await update.message.reply_text(
                "❌ لطفاً فقط عدد را بر اساس دقیقه ارسال کنید."
            )

            return

        try:

            minutes = int(update.message.text.strip())

        except ValueError:

            await update.message.reply_text("""❌ مقدار نامعتبر است.

لطفاً فقط یک عدد صحیح بر اساس دقیقه ارسال کنید.
مثال: 1 یا 20 یا 120""")

            return

        if minutes < 1:

            await update.message.reply_text(
                "❌ زمان‌بندی نمی‌تواند کمتر از ۱ دقیقه باشد."
            )

            return

        group_db_id = context.user_data.get("group_schedule_id")

        if not group_db_id:

            context.user_data["state"] = State.NONE

            await update.message.reply_text("❌ اطلاعات گروه پیدا نشد.")

            return

        from database import set_group_schedule

        set_group_schedule(
            registered_group_id=group_db_id,
            user_id=update.effective_user.id,
            minutes=minutes,
        )

        context.user_data["state"] = State.NONE

        # -----------------------------------------
        # حذف پیام عددی کاربر
        # -----------------------------------------

        try:

            await update.message.delete()

        except Exception:

            pass

        # -----------------------------------------
        # حذف پیام قبلی پنل / راهنما
        # -----------------------------------------

        old_panel_id = context.user_data.pop(
            "group_info_message_id",
            None,
        )

        prompt_id = context.user_data.pop(
            "group_schedule_prompt_id",
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

        # -----------------------------------------
        # نمایش دوباره پنل در پایین چت
        # -----------------------------------------

        from handlers.connect_account import show_group_info_panel

        await show_group_info_panel(
            context=context,
            chat_id=update.effective_chat.id,
            group_db_id=group_db_id,
            user_id=update.effective_user.id,
            old_message_id=old_panel_id,
        )
        return

    user_data = context.user_data or {}

    state = user_data.get("state", State.NONE)

    if state == State.SOURCE_CHANNEL:
        return await receive_source_channel(update, context)

    if state == State.TARGET_CHANNEL:
        return await receive_target_channel(update, context)

    if state == "WAIT_API_ID":

        from database import save_api_id

        api_id = update.message.text.strip()

        save_api_id(
            update.effective_user.id,
            api_id,
        )

        context.user_data["state"] = "WAIT_API_HASH"

        await update.message.reply_text("""✅ API ID ذخیره شد.

حالا API HASH رو همینجا برام ارسال کن.""")

        return

    if state == "WAIT_API_HASH":

        from database import save_api_hash

        api_hash = update.message.text.strip()

        save_api_hash(
            update.effective_user.id,
            api_hash,
        )

        context.user_data["state"] = "WAIT_PHONE"

        await update.message.reply_text("""✅ API HASH هم ذخیره شد.

حالا شماره تلگرامت رو با فرمت زیر ارسال کن:
+989123456789
شماره اکانتی که api id  و  hash id اون رو فرستادی.""")

        return

    if state == "WAIT_PHONE":

        from database import save_phone, get_account

        user_id = update.effective_user.id
        phone = update.message.text.strip()

        account = get_account(user_id)

        if not account:
            await update.message.reply_text("❌ اطلاعات اتصال اکانت پیدا نشد.")
            context.user_data["state"] = State.NONE
            return

        api_id = account[1]
        api_hash = account[2]

        if not api_id or not api_hash:
            await update.message.reply_text("❌ ابتدا API ID و API HASH را وارد کنید.")
            context.user_data["state"] = State.NONE
            return

        try:
            api_id = int(api_id)
        except (TypeError, ValueError):

            await update.message.reply_text("❌ API ID معتبر نیست.")

            context.user_data["state"] = State.NONE
            return

        save_phone(
            user_id,
            phone,
        )

        status_message = await update.message.reply_text("⏳ در حال ارسال کد ورود...")

        client = TelegramClient(
            StringSession(),
            api_id,
            api_hash,
        )

        try:

            await client.connect()

            sent_code = await client.send_code_request(phone)

            # نگه داشتن Client و phone_code_hash
            context.user_data["login_client"] = client
            context.user_data["phone_code_hash"] = sent_code.phone_code_hash
            context.user_data["login_phone"] = phone

            context.user_data["state"] = "WAIT_CODE"

            try:
                await status_message.delete()
            except Exception:
                pass

            await update.message.reply_text(
                """📩 <b>کد ورود ارسال شد.</b>

کدی که تلگرام برای اکانت شما ارسال کرده را همینجا بفرستید.

⚠️ کد ورود را فقط همینجا ارسال کنید.""",
                parse_mode="HTML",
            )

        except Exception as e:

            try:
                await client.disconnect()
            except Exception:
                pass

            try:
                await status_message.delete()
            except Exception:
                pass

            await update.message.reply_text(
                "❌ ارسال کد ورود انجام نشد.\n\n"
                "شماره و API اطلاعات خود را بررسی کنید."
            )

            context.user_data.pop(
                "login_client",
                None,
            )

            context.user_data.pop(
                "phone_code_hash",
                None,
            )

            context.user_data["state"] = "WAIT_PHONE"

        return

    if state == "WAIT_CODE":

        from database import save_session

        user_id = update.effective_user.id
        code = update.message.text.strip()

        client = context.user_data.get("login_client")

        phone = context.user_data.get("login_phone")

        phone_code_hash = context.user_data.get("phone_code_hash")

        if not client or not phone or not phone_code_hash:

            await update.message.reply_text(
                "❌ نشست ورود پیدا نشد.\n\n" "لطفاً اتصال اکانت را از ابتدا انجام دهید."
            )

            context.user_data["state"] = State.NONE
            return

        try:

            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=phone_code_hash,
            )

            session_string = client.session.save()

            save_session(
                user_id,
                session_string,
            )

            await client.disconnect()

            context.user_data.pop(
                "login_client",
                None,
            )

            context.user_data.pop(
                "phone_code_hash",
                None,
            )

            context.user_data.pop(
                "login_phone",
                None,
            )

            context.user_data["state"] = State.NONE

            await update.message.reply_text(
                """✅ <b>اکانت با موفقیت متصل شد.</b>

🔐 نشست اکانت ذخیره شد و اتصال با موفقیت انجام شد.""",
                parse_mode="HTML",
            )

        except PhoneCodeInvalidError:

            await update.message.reply_text(
                "❌ کد ورود اشتباه است.\n\n" "لطفاً کد صحیح را ارسال کنید."
            )

            return

        except PhoneCodeExpiredError:

            try:
                await client.disconnect()
            except Exception:
                pass

            context.user_data.pop(
                "login_client",
                None,
            )

            context.user_data.pop(
                "phone_code_hash",
                None,
            )

            context.user_data.pop(
                "login_phone",
                None,
            )

            context.user_data["state"] = State.NONE

            await update.message.reply_text(
                "❌ کد ورود منقضی شده است.\n\n" "لطفاً اتصال اکانت را دوباره شروع کنید."
            )

            return

        except SessionPasswordNeededError:

            context.user_data["state"] = "WAIT_2FA_PASSWORD"

            await update.message.reply_text(
                """🔐 <b>تأیید دومرحله‌ای فعال است.</b>

رمز دومرحله‌ای اکانت تلگرام را ارسال کنید.""",
                parse_mode="HTML",
            )

            return

        except Exception as e:

            pass

            try:
                await client.disconnect()
            except Exception:
                pass

            context.user_data.pop(
                "login_client",
                None,
            )

            context.user_data["state"] = State.NONE

            await update.message.reply_text(
                "❌ اتصال اکانت انجام نشد.\n\n" "لطفاً دوباره تلاش کنید."
            )

            return

    if state == "WAIT_2FA_PASSWORD":

        from database import save_session

        password = update.message.text

        client = context.user_data.get("login_client")

        if not client:
            context.user_data["state"] = State.NONE

            await update.message.reply_text(
                "❌ نشست ورود پیدا نشد.\n\nلطفاً دوباره اتصال اکانت را شروع کنید."
            )
            return

        try:

            await client.sign_in(password=password)

            if not await client.is_user_authorized():
                await update.message.reply_text("❌ ورود انجام نشد.")
                return

            session_string = client.session.save()

            save_session(
                update.effective_user.id,
                session_string,
            )

            await client.disconnect()

            context.user_data.pop("login_client", None)
            context.user_data.pop("login_phone", None)
            context.user_data.pop("phone_code_hash", None)

            context.user_data["state"] = State.NONE

            await update.message.reply_text("✅ اکانت با موفقیت متصل شد.")

        except SessionPasswordNeededError:

            await update.message.reply_text(
                "🔐 این اکانت دارای تایید دومرحله‌ای است.\n\n"
                "رمز دومرحله‌ای را ارسال کنید."
            )

            context.user_data["state"] = State.WAIT_2FA_PASSWORD

        except PasswordHashInvalidError:

            await update.message.reply_text(
                "❌ رمز دومرحله‌ای اشتباه است.\n\n" "دوباره رمز را ارسال کنید."
            )

            context.user_data["state"] = State.WAIT_2FA_PASSWORD

        except Exception as e:

            pass

            await update.message.reply_text(f"❌ خطا:\n{type(e).name}")

            context.user_data["state"] = State.WAIT_2FA_PASSWORD

        return

    return


# =========================
# CREATE BOT
# =========================


def create_bot():
    app = Application.builder().token(config.BOT_TOKEN).build()

    from telegram.ext import CallbackQueryHandler

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern=r"^check_join$"))
    app.add_handler(CallbackQueryHandler(transfer_info, pattern=r"^transfer_\d+$"))
    app.add_handler(
        CallbackQueryHandler(delete_transfer_callback, pattern=r"^delete_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(toggle_transfer_callback, pattern=r"^toggle_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(
            back_to_registered_channels, pattern=r"^registered_channels$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            registered_channels_list,
            pattern=r"^registered_channel$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            registered_groups_list,
            pattern=r"^registered_group$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            registered_group_info,
            pattern=r"^registered_group_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_group_callback,
            pattern=r"^delete_group_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            confirm_delete_group_callback,
            pattern=r"^confirm_delete_group_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            cancel_delete_group_callback,
            pattern=r"^cancel_delete_group_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            registered_back_menu,
            pattern=r"^registered_back$",
        )
    )

    app.add_handler(CallbackQueryHandler(transfer_settings, pattern=r"^settings_\d+$"))
    app.add_handler(
        CallbackQueryHandler(remove_lines_setting, pattern=r"^remove_lines_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(append_lines_setting, pattern=r"^append_lines_\d+$")
    )
    app.add_handler(CallbackQueryHandler(finish_transfer, pattern=r"^finish_transfer$"))
    app.add_handler(
        CallbackQueryHandler(change_source_callback, pattern=r"^change_source_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(confirm_source_callback, pattern=r"^confirm_source_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(cancel_source_callback, pattern=r"^cancel_source_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(change_target_callback, pattern=r"^change_target_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(confirm_target_callback, pattern=r"^confirm_target_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(cancel_target_callback, pattern=r"^cancel_target_\d+$")
    )
    app.add_handler(
        CallbackQueryHandler(finish_change_target, pattern=r"^finish_change_target$")
    )

    app.add_handler(
        CallbackQueryHandler(
            group_message_callback,
            pattern=r"^group_message_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            group_schedule_callback,
            pattern=r"^group_schedule_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            start_group_ads_callback,
            pattern=r"^start_group_ads_\d+$",
        )
    )

    app.add_handler(
        CommandHandler(
            "admin",
            admin_panel,
        )
    )

    app.add_handler(CallbackQueryHandler(buttons))

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            text_buttons,
        ),
        group=1,
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            conversation_router,
        ),
        group=2,
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            admin_reply,
        ),
        group=100,
    )

    app.bot_data["tg_client"] = tg_client

    async def startup(app):
        try:
            await tg_client.start()
        except Exception:
            pass

        try:
            from listener import start_all_listeners

            await start_all_listeners()
        except Exception:
            pass

    app.post_init = startup

    return app
