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
    MessageHandler,
    ContextTypes,
    filters,
)

from handlers.connect_account import (
    connect_account,
    receive_source_channel,
    receive_target_channel,
)

from handlers.connect_account import (
    delete_transfer_callback,
    toggle_transfer_callback,
    back_to_registered_channels,
    transfer_settings,
    remove_lines_setting,
)

import config
from telegram_client import tg_client
from handlers.connect_account import registered_channels
from handlers.connect_account import transfer_info
from database import set_remove_last_lines
from handlers.connect_account import append_lines_setting
from database import set_append_last_lines

# ---------------------- clear waiting state --------------------


def clear_waiting_state(context):
    context.user_data["state"] = State.NONE


# ---------------------- training keyboard --------------------


def training_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚠️ نکات مهم",
                    callback_data="training_rules",
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 اتصال کانال‌ها",
                    callback_data="training_connect",
                )
            ],
            [
                InlineKeyboardButton(
                    "⚙️ تنظیمات ارسال پست",
                    callback_data="training_settings",
                )
            ],
            [
                InlineKeyboardButton(
                    "✂️ حذف خطوط آخر",
                    callback_data="training_delete_lines",
                )
            ],
            [
                InlineKeyboardButton(
                    "✍️ افزودن خطوط آخر",
                    callback_data="training_add_lines",
                )
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


# =========================
# START
# =========================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = ReplyKeyboardMarkup(
        [
            ["📢 افزودن کانال"],
            ["📋 کانال‌های ثبت شده"],
            ["📚 آموزش استفاده"],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        """🚀 به ربات runspace خوش آمدید.

با این ربات می‌توانید:

• یک کانال مبدا انتخاب کنید.
• یک کانال مقصد انتخاب کنید.
• پست‌های کانال مبدا را به صورت خودکار در مقصد منتشر کنید.""",
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

    if query.data == "training_settings":

        await training_settings(
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
        "<b>⚠️ نکات مهم</b>\n\n"
        "برای اینکه ربات بدون مشکل کار کند، حتماً موارد زیر را رعایت کنید:\n\n"
        "🔹 <b>ربات</b> باید در کانال مقصد <b>ادمین</b> باشد و اجازه ارسال پیام داشته باشد.\n\n"
        "🔹 <b>اکانت متصل به ربات</b> هم باید در کانال مقصد ادمین باشد.\n\n"
        "اکانت متصل:\n"
        "<code>@egpora_e3</code>\n\n"
        "⚠️ پیشنهاد می‌شود هنگام ادمین کردن، تمام دسترسی‌ها مخصوصاً <b>ارسال پیام</b> فعال باشد.\n\n"
        "در صورت نداشتن دسترسی لازم، ربات نمی‌تواند پست‌ها را در کانال مقصد ارسال کند.",
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


# --------------------- training settings -------------------


async def training_settings(update, context):

    query = update.callback_query

    await query.edit_message_text(
        "<b>⚙️ تنظیمات ارسال پست</b>\n\n"
        "در این بخش می‌توانید نحوه ارسال پست‌ها از کانال مبدا "
        "به کانال مقصد را شخصی‌سازی کنید.\n\n"
        "با استفاده از تنظیمات می‌توانید متن پست‌ها را تغییر دهید، "
        "بخشی از متن را حذف کنید یا متن دلخواه خودتان را به پست‌ها اضافه کنید.\n\n"
        "برای تنظیم هر بخش، از گزینه‌های مربوط به تنظیمات استفاده کنید. ✅",
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

    text = update.message.text

    MAIN_BUTTONS = [
        "📢 افزودن کانال",
        "📋 کانال‌های ثبت شده",
        "📚 آموزش استفاده",
    ]

    if text in MAIN_BUTTONS:
        clear_waiting_state(context)

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

            await update.message.reply_text("❌ لطفاً فقط عدد ارسال کنید.\nمثال: 8")

            return

        transfer_id = context.user_data.get("remove_lines_transfer_id")

        if transfer_id:

            set_remove_last_lines(
                transfer_id,
                count,
            )

        context.user_data["state"] = State.NONE

        await update.message.reply_text(
            f"✅ تنظیم شد.\n" f"از این به بعد {count} خط آخر پست‌ها حذف می‌شود."
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

        await update.message.reply_text(
            "✅ متن جدید ذخیره شد.\n" "از این به بعد به آخر پست‌ها اضافه می‌شود."
        )

        return

    # =========================
    # دریافت کانال مقصد
    # =========================

    if state == State.TARGET_CHANNEL:

        await receive_target_channel(update, context)

        return

    # =========================
    # دکمه‌های اصلی
    # =========================
    if text == "📢 افزودن کانال":

        await connect_account(
            update,
            context,
        )

        return

    if text == "📋 کانال‌های ثبت شده":

        await registered_channels(
            update,
            context,
        )

        return

    if text == "📚 آموزش استفاده":

        await show_training_menu(update, context)

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
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_buttons,
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

    app.add_handler(CallbackQueryHandler(buttons))
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
