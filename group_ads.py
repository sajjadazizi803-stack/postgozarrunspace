import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    InputPeerChannel,
    MessageEntityBlockquote,
)

import config
import json

from database import (
    get_user_groups,
    get_group_message,
    set_group_enabled,
    get_account,
)

# =========================================================
# GROUP ADS WORKERS
# =========================================================

group_ads_tasks = {}

user_clients = {}


# =========================================================
# USER CLIENT
# =========================================================


async def get_user_client(user_id):

    if user_id in user_clients:

        client = user_clients[user_id]

        if client.is_connected():

            return client

        try:
            await client.connect()

            if await client.is_user_authorized():
                return client

        except Exception:
            pass

        try:
            await client.disconnect()
        except Exception:
            pass

        user_clients.pop(user_id, None)

    account = get_account(user_id)

    if not account:
        raise RuntimeError("اکانت کاربر پیدا نشد.")

    api_id = account[1]
    api_hash = account[2]
    session_string = account[4]

    if not api_id or not api_hash or not session_string:
        raise RuntimeError("اطلاعات Session اکانت کامل نیست.")

    client = TelegramClient(
        StringSession(session_string),
        int(api_id),
        api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():

        await client.disconnect()

        raise RuntimeError("Session اکانت معتبر نیست.")

    user_clients[user_id] = client

    return client


# ------------------ build quote message -----------------


def build_quote_message(
    message_text,
    quote_text,
):
    if not quote_text:
        return message_text, None

    message_text = message_text or ""

    if message_text:
        final_text = f"{quote_text}\n\n{message_text}"
    else:
        final_text = quote_text

    # Telegram entities use UTF-16 offsets
    quote_length = len(quote_text.encode("utf-16-le")) // 2

    quote_entity = MessageEntityBlockquote(
        offset=0,
        length=quote_length,
    )

    return final_text, [quote_entity]


# ---------------------- build blockquote_entities ----------------


def build_blockquote_entities(entities_json):
    if not entities_json:
        return None

    try:
        data = json.loads(entities_json)
    except Exception:
        return None

    entities = []

    for item in data:
        entity_type = item.get("type")
        offset = item.get("offset")
        length = item.get("length")

        if offset is None or length is None:
            continue

        if entity_type == "blockquote":
            entities.append(
                MessageEntityBlockquote(
                    offset=offset,
                    length=length,
                    collapsed=False,
                )
            )

        elif entity_type == "expandable_blockquote":
            entities.append(
                MessageEntityBlockquote(
                    offset=offset,
                    length=length,
                    collapsed=True,
                )
            )

    return entities or None


# =========================================================
# SEND SAVED MESSAGE
# =========================================================


async def send_group_message(
    user_id,
    group_db_id,
):

    client = await get_user_client(user_id)

    groups = get_user_groups(user_id)

    group = None

    for item in groups:

        if item[0] == group_db_id:

            group = item
            break

    if group is None:

        raise RuntimeError("گروه پیدا نشد.")

    group_id = group[1]
    access_hash = group[2]

    # -----------------------------------------
    # گرفتن Entity گروه
    # -----------------------------------------

    try:

        entity = await client.get_entity(group_id)

    except Exception:

        if not access_hash:

            raise

        entity = await client.get_entity(
            InputPeerChannel(
                group_id,
                access_hash,
            )
        )

    # -----------------------------------------
    # گرفتن پیام ذخیره‌شده
    # -----------------------------------------

    group_message = get_group_message(
        group_db_id,
        user_id,
    )

    if not group_message:

        raise RuntimeError("پیام تبلیغاتی ثبت نشده.")

    message_type = group_message[3]

    message_text = group_message[4]

    caption = group_message[5]

    file_path = group_message[6]

    forward_chat_id = group_message[7]

    forward_message_id = group_message[8]

    quote_text = group_message[12]

    entities_json = group_message[13]

    # =========================================
    # TEXT
    # =========================================

    if message_type == "text":

        if not message_text and not quote_text:
            raise RuntimeError("متن پیام خالی است.")

        final_text, formatting_entities = build_quote_message(
            message_text,
            quote_text,
        )

    saved_entities = build_blockquote_entities(entities_json)

    if saved_entities:
        formatting_entities = saved_entities

        await client.send_message(
            entity,
            final_text,
            formatting_entities=formatting_entities,
        )

        return

    # =========================================
    # FORWARD
    # =========================================

    if message_type == "forward":

        if not forward_chat_id or not forward_message_id:

            raise RuntimeError("اطلاعات پیام فوروارد پیدا نشد.")

        source_entity = await client.get_entity(forward_chat_id)

        await client.forward_messages(
            entity,
            forward_message_id,
            from_peer=source_entity,
        )

        return

    # =========================================
    # MEDIA
    # =========================================

    if file_path:

        path = Path(file_path)

        if not path.exists():

            raise RuntimeError(f"فایل پیام پیدا نشد: {file_path}")

        final_caption, formatting_entities = build_quote_message(
            caption,
            quote_text,
        )

    saved_entities = build_blockquote_entities(entities_json)

    if saved_entities:
        formatting_entities = saved_entities

        send_kwargs = {
            "caption": final_caption,
            "formatting_entities": formatting_entities,
        }

        await client.send_file(
            entity,
            str(path),
            **send_kwargs,
        )

        return

    raise RuntimeError("اطلاعات پیام تبلیغاتی ناقص است.")


# =========================================================
# ONE GROUP WORKER
# =========================================================


async def group_ads_worker(
    user_id,
    group_db_id,
):

    key = group_db_id

    while True:

        try:

            groups = get_user_groups(user_id)

            group = None

            for item in groups:

                if item[0] == group_db_id:

                    group = item
                    break

            # -----------------------------------------
            # گروه حذف شده
            # -----------------------------------------

            if group is None:

                break

            # -----------------------------------------
            # تبلیغات متوقف شده
            # -----------------------------------------

            enabled = bool(group[6])

            if not enabled:

                break

            # -----------------------------------------
            # پیام
            # -----------------------------------------

            group_message = get_group_message(
                group_db_id,
                user_id,
            )

            if not group_message:

                set_group_enabled(
                    registered_group_id=group_db_id,
                    user_id=user_id,
                    enabled=False,
                )

                break

            schedule_minutes = group_message[9]

            if not schedule_minutes or schedule_minutes < 1:

                set_group_enabled(
                    registered_group_id=group_db_id,
                    user_id=user_id,
                    enabled=False,
                )

                break

            # -----------------------------------------
            # صبر تا نوبت ارسال بعدی
            # -----------------------------------------

            await asyncio.sleep(schedule_minutes * 60)

            # -----------------------------------------
            # دوباره بررسی وضعیت
            # -----------------------------------------

            groups = get_user_groups(user_id)

            group = None

            for item in groups:

                if item[0] == group_db_id:

                    group = item
                    break

            if group is None:

                break

            if not bool(group[6]):

                break

            # -----------------------------------------
            # ارسال
            # -----------------------------------------

            await send_group_message(
                user_id=user_id,
                group_db_id=group_db_id,
            )

        except asyncio.CancelledError:

            break

        except Exception as e:

            pass

            # اگر خطا موقتی بود، Worker نمی‌میرد.
            await asyncio.sleep(10)

    group_ads_tasks.pop(key, None)


# =========================================================
# START WORKER
# =========================================================


async def start_group_ads_worker(
    user_id,
    group_db_id,
):

    existing = group_ads_tasks.get(group_db_id)

    if existing and not existing.done():

        return

    task = asyncio.create_task(
        group_ads_worker(
            user_id=user_id,
            group_db_id=group_db_id,
        )
    )

    group_ads_tasks[group_db_id] = task


# =========================================================
# STOP WORKER
# =========================================================


async def stop_group_ads_worker(
    group_db_id,
):

    task = group_ads_tasks.pop(
        group_db_id,
        None,
    )

    if not task:

        return

    if not task.done():

        task.cancel()

        try:

            await task

        except asyncio.CancelledError:

            pass


# =========================================================
# START ALL ACTIVE GROUPS
# =========================================================


async def start_all_group_ads():

    # برای پیدا کردن userها از خود groupها استفاده می‌کنیم.
    # user_id ها را از دیتابیس می‌گیریم.

    from database import get_all_active_group_ads

    groups = get_all_active_group_ads()

    for item in groups:

        user_id = item[0]
        group_db_id = item[1]

        try:

            await start_group_ads_worker(
                user_id=user_id,
                group_db_id=group_db_id,
            )

        except Exception as e:

            pass


# =========================================================
# SHUTDOWN
# =========================================================


async def shutdown_group_ads():

    tasks = list(group_ads_tasks.values())

    for task in tasks:

        if not task.done():

            task.cancel()

    if tasks:

        await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

    group_ads_tasks.clear()

    for client in list(user_clients.values()):

        try:

            await client.disconnect()

        except Exception:

            pass

    user_clients.clear()
