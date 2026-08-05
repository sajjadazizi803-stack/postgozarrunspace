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
)

from handlers.ads import (
    ads_buttons,
    receive_group,
    receive_interval,
    WAIT_GROUP,
    WAIT_INTERVAL,
)

from handlers.connect_account import (
    connect_account,
    receive_source_channel,
    receive_target_channel,
    finish_transfer,
)

from handlers.connect_account import (
    delete_transfer_callback,
    toggle_transfer_callback,
    back_to_registered_channels,
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
from handlers.ads import ads_panel
from conversation import State

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
    context.user_data.pop("conversation", None)
    context.user_data.pop("wait_group", None)


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
                    "💬 ارتباط با پشتیبانی",
                ],
            ],
            resize_keyboard=True,
        )

        await query.message.edit_text(
            f"""👋 <b>سلام {query.from_user.first_name}، به ربات مدیریت کانال | RunSpace خوش اومدی 🚀</b>

✨ با این ربات می‌تونی کانالت رو بهتر مدیریت کنی.

⚠️ <b>قبل از استفاده، حتماً نکات مهم رو از بخش آموزش بخون.</b>""",
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
                        "💬 ارتباط با پشتیبانی",
                    ],
                ],
                resize_keyboard=True,
            )

            if not context.user_data.get("started"):

                context.user_data["started"] = True

                await update.message.reply_text(
                    f"""👋 <b>سلام {first_name}، به ربات مدیریت کانال | RunSpace خوش اومدی 🚀</b>

✨ با این ربات می‌تونی کانالت رو بهتر مدیریت کنی.

⚠️ <b>قبل از استفاده، حتماً نکات مهم رو از بخش آموزش بخون.</b>""",
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

    if query.data == "training_back":

        await query.edit_message_text(
            "📚 <b>آموزش استفاده از ربات</b>\n\n"
            "برای مشاهده آموزش هر بخش، روی دکمه مورد نظر کلیک کنید.\n\n"
            "پیشنهاد می‌شود تمام بخش‌ها را با دقت مطالعه کنید "
            "تا بتوانید بهتر از ربات استفاده کنید. ✅",
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

    await query.edit_message_text(
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


# --------------------- training connect -------------------


async def training_connect(update, context):

    query = update.callback_query

    await query.edit_message_text(
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
                        "🔙 بازگشت به آموزش", callback_data="training_back"
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )


# --------------------- training delete lines -------------------


async def training_delete_lines(update, context):

    query = update.callback_query

    await query.edit_message_text(
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


# --------------------- training add lines -------------------


async def training_add_lines(update, context):

    query = update.callback_query

    await query.edit_message_text(
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

    if user_data is None:
        return

    text = update.message.text if update.message.text else ""

    MAIN_BUTTONS = [
        "➕ افزودن انتقال",
        "📋 انتقال‌های ثبت شده",
        "📚 آموزش استفاده",
        "💬 ارتباط با پشتیبانی",
        "📢 کانال",
        "👥 گروه",
        "🔙",
    ]

    if text in MAIN_BUTTONS:

        clear_waiting_state(context)

        user_data["state"] = State.NONE

    state = user_data.get("state", State.NONE)

    # =========================
    # دریافت کانال مبدا
    # =========================

    if state == State.SOURCE_CHANNEL:

        await receive_source_channel(update, context)

        return

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

        return

    # =========================
    # انتخاب نوع افزودن
    # =========================

    if text == "➕ افزودن انتقال":

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

    if text == "📢 کانال":

        await connect_account(update, context)

        return

    if text == "👥 گروه":

        await add_group(update, context)

        return

    if text == "🔙":

        keyboard = ReplyKeyboardMarkup(
            [
                [
                    "➕ افزودن انتقال",
                    "📋 انتقال‌های ثبت شده",
                ],
                [
                    "📚 آموزش استفاده",
                    "💬 ارتباط با پشتیبانی",
                ],
            ],
            resize_keyboard=True,
        )

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

    user_data = context.user_data or {}

    state = user_data.get("state", State.NONE)

    if state == State.SOURCE_CHANNEL:
        return await receive_source_channel(update, context)

    if state == State.TARGET_CHANNEL:
        return await receive_target_channel(update, context)

    return


# =========================
# CREATE BOT
# =========================


def create_bot():

    app = Application.builder().token(config.BOT_TOKEN).build()

    from telegram.ext import CallbackQueryHandler

    app.add_handler(
        CallbackQueryHandler(
            check_join,
            pattern="^check_join$",
        )
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "ads",
            ads_panel,
        )
    )

    ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                ads_buttons,
                pattern="^ads_add_group$",
            ),
            CallbackQueryHandler(
                ads_buttons,
                pattern="^ads_time_.*$",
            ),
        ],
        states={
            WAIT_GROUP: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_group,
                )
            ],
            WAIT_INTERVAL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_interval,
                )
            ],
        },
        fallbacks=[],
        per_message=False,
    )

    app.add_handler(
        CallbackQueryHandler(
            ads_buttons,
            pattern=r"^ads_",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            transfer_info,
            pattern=r"^transfer_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_transfer_callback,
            pattern=r"^delete_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            toggle_transfer_callback,
            pattern=r"^toggle_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            back_to_registered_channels,
            pattern=r"^registered_channels$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            transfer_settings,
            pattern=r"^settings_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            remove_lines_setting,
            pattern=r"^remove_lines_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            append_lines_setting,
            pattern=r"^append_lines_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            finish_transfer,
            pattern=r"^finish_transfer$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            change_source_callback,
            pattern=r"^change_source_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            confirm_source_callback,
            pattern=r"^confirm_source_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            cancel_source_callback,
            pattern=r"^cancel_source_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            change_target_callback,
            pattern=r"^change_target_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            confirm_target_callback,
            pattern=r"^confirm_target_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            cancel_target_callback,
            pattern=r"^cancel_target_\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            finish_change_target,
            pattern=r"^finish_change_target$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            buttons,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            text_buttons,
        )
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
