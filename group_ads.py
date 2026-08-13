import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerChannel

import config

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

    # =========================================
    # TEXT
    # =========================================

    if message_type == "text":

        if not message_text:

            raise RuntimeError("متن پیام خالی است.")

        await client.send_message(
            entity,
            message_text,
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

        send_kwargs = {}

        if caption:

            send_kwargs["caption"] = caption

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

    print(f"[GROUP ADS] Worker started: " f"user={user_id}, group={group_db_id}")

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

                print(f"[GROUP ADS] Group removed: {group_db_id}")

                break

            # -----------------------------------------
            # تبلیغات متوقف شده
            # -----------------------------------------

            enabled = bool(group[6])

            if not enabled:

                print(f"[GROUP ADS] Worker stopped: " f"group={group_db_id}")

                break

            # -----------------------------------------
            # پیام
            # -----------------------------------------

            group_message = get_group_message(
                group_db_id,
                user_id,
            )

            if not group_message:

                print(f"[GROUP ADS] Message missing: " f"group={group_db_id}")

                set_group_enabled(
                    registered_group_id=group_db_id,
                    user_id=user_id,
                    enabled=False,
                )

                break

            schedule_minutes = group_message[9]

            if not schedule_minutes or schedule_minutes < 1:

                print(f"[GROUP ADS] Schedule missing: " f"group={group_db_id}")

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

            print(f"[GROUP ADS] Sent successfully: " f"group={group_db_id}")

        except asyncio.CancelledError:

            print(f"[GROUP ADS] Cancelled: " f"group={group_db_id}")

            break

        except Exception as e:

            print(f"[GROUP ADS ERROR] " f"group={group_db_id}: {e}")

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

        print(f"[GROUP ADS] Worker already exists: " f"group={group_db_id}")

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

    print("[GROUP ADS] Checking active groups...")

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

            print(f"[GROUP ADS START ERROR] " f"group={group_db_id}: {e}")


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
