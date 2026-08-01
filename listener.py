from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest

import asyncio

from database import get_all_transfers, increase_sent_count
from telegram_client import tg_client

# =========================
# Global
# =========================

registered_listeners = set()

polling_tasks = {}

last_messages = {}

event_handlers = {}


# =========================
# Transfer Message
# =========================


async def transfer_message(
    client: TelegramClient,
    message,
    target_entity,
    transfer_id=None,
):
    """
    انتقال یک پیام از مبدا به مقصد
    """

    try:

        if message.media:

            file = await message.download_media()

            if not file:
                return False

            try:

                await client.send_file(
                    entity=target_entity,
                    file=file,
                    caption=message.text or "",
                )

            finally:

                try:
                    import os

                    if os.path.exists(file):
                        os.remove(file)

                except Exception:
                    pass

        else:

            text = message.text or ""

            if not text:
                return False

            await client.send_message(
                entity=target_entity,
                message=text,
            )

        if transfer_id is not None:

            try:
                increase_sent_count(transfer_id)
            except Exception as e:
                print(f"COUNT ERROR: {e}")

        return True

    except Exception as e:

        print(f"TRANSFER ERROR: {e}")

        return False


# =========================
# Polling Worker
# =========================


async def polling_worker(
    client: TelegramClient,
    source_entity,
    target_entity,
    transfer_id,
):
    """
    هر ۲ ثانیه تاریخچه کانال را مستقیماً از Telegram API بررسی می‌کند.

    این Worker وابسته به باز شدن کانال در Telegram Client نیست.
    """

    source_id = source_entity.id

    transfer_key = (
        source_id,
        target_entity.id,
    )

    print(f"🔄 Polling Started: " f"{source_entity.id} -> {target_entity.id}")

    try:

        # ---------------------------------
        # تعیین آخرین پیام موجود در شروع
        # ---------------------------------

        if transfer_key not in last_messages:

            try:

                history = await client(
                    GetHistoryRequest(
                        peer=source_entity,
                        offset_id=0,
                        offset_date=None,
                        add_offset=0,
                        limit=1,
                        max_id=0,
                        min_id=0,
                        hash=0,
                    )
                )

                if history.messages:

                    latest_message = history.messages[0]

                    last_messages[transfer_key] = latest_message.id

                    print(
                        f"📌 Initial Message ID "
                        f"{latest_message.id} "
                        f"for {source_entity.id}"
                    )

                else:

                    last_messages[transfer_key] = 0

            except Exception as e:

                print(f"INITIAL POLL ERROR " f"{source_entity.id}: {e}")

                last_messages[transfer_key] = 0

        # ---------------------------------
        # Main Polling Loop
        # ---------------------------------

        while True:

            try:

                last_id = last_messages.get(
                    transfer_key,
                    0,
                )
                history = await client(
                    GetHistoryRequest(
                        peer=source_entity,
                        offset_id=0,
                        offset_date=None,
                        add_offset=0,
                        limit=100,
                        max_id=0,
                        min_id=last_id,
                        hash=0,
                    )
                )

                messages = history.messages

                if messages:

                    # قدیمی -> جدید
                    messages = sorted(
                        messages,
                        key=lambda x: x.id,
                    )

                    for message in messages:

                        if message.id <= last_id:
                            continue

                        # اول ID را ثبت می‌کنیم
                        # تا Event دوباره آن را نفرستد
                        last_messages[transfer_key] = message.id

                        await transfer_message(
                            client=client,
                            message=message,
                            target_entity=target_entity,
                            transfer_id=transfer_id,
                        )

                        last_id = message.id

                        await asyncio.sleep(0.1)

            except asyncio.CancelledError:

                print(
                    f"🛑 Polling Stopped: " f"{source_entity.id} -> {target_entity.id}"
                )

                raise

            except Exception as e:

                print(
                    f"❌ POLLING ERROR "
                    f"{source_entity.id} -> "
                    f"{target_entity.id}: {e}"
                )

            await asyncio.sleep(2)

    finally:

        polling_tasks.pop(
            transfer_key,
            None,
        )


# =========================
# Register Listener
# =========================


async def register_listener(
    client: TelegramClient,
    source_channel,
    target_channel,
    transfer_id=None,
):

    key = (
        source_channel,
        target_channel,
    )

    if key in registered_listeners:

        print(f"⚠️ Already Registered: " f"{source_channel} -> {target_channel}")

        return

    try:

        source_entity = await client.get_entity(source_channel)

        target_entity = await client.get_entity(target_channel)

        source_id = source_entity.id
        target_id = target_entity.id

        transfer_key = (
            source_id,
            target_id,
        )

    except Exception as e:

        print(f"❌ REGISTER ERROR: {e}")

        return

    # =====================================
    # Event Handler
    # =====================================

    async def new_post(event):

        try:

            if not event.chat:
                return

            if event.chat.id != source_id:
                return

            message = event.message

            if not message:
                return

            message_id = message.id

            current_last_id = last_messages.get(
                transfer_key,
                0,
            )

            # اگر قبلاً Polling این پیام را دیده
            # دوباره ارسال نکن
            if message_id <= current_last_id:
                return

            # ID را قبل از ارسال ثبت کن
            last_messages[transfer_key] = message_id

            await transfer_message(
                client=client,
                message=message,
                target_entity=target_entity,
                transfer_id=transfer_id,
            )

        except Exception as e:

            print(f"❌ EVENT ERROR: {e}")

    # =====================================
    # ثبت Event Handler فقط یک بار
    # =====================================

    client.add_event_handler(
        new_post,
        events.NewMessage(chats=source_entity),
    )

    event_handlers[transfer_key] = new_post

    # =====================================
    # ثبت Listener
    # =====================================

    registered_listeners.add(key)

    # =====================================
    # فقط یک Polling برای هر اتصال
    # =====================================

    if transfer_key not in polling_tasks:

        task = asyncio.create_task(
            polling_worker(
                client=client,
                source_entity=source_entity,
                target_entity=target_entity,
                transfer_id=transfer_id,
            )
        )

        polling_tasks[transfer_key] = task

    print(f"✅ Listener Registered: " f"{source_channel} -> {target_channel}")


# =========================
# Start All Listeners
# =========================


async def start_all_listeners():

    if not tg_client.is_connected():

        await tg_client.connect()

    transfers = get_all_transfers()

    for transfer in transfers:

        transfer_id = transfer[0]
        telegram_id = transfer[1]
        source = transfer[2]
        target = transfer[3]
        enabled = transfer[4]

        if enabled != 1:
            continue

        try:

            await register_listener(
                client=tg_client,
                source_channel=source,
                target_channel=target,
                transfer_id=transfer_id,
            )

        except Exception as e:

            print(f"❌ START LISTENER ERROR " f"{source} -> {target}: {e}")


# =========================
# Add New Transfer
# =========================


async def add_new_transfer(
    telegram_id,
    source_channel,
    target_channel,
):
    """
    فعال کردن انتقال جدید بدون Restart
    """

    transfers = get_all_transfers()

    transfer_id = None

    for transfer in transfers:

        if (
            transfer[1] == telegram_id
            and transfer[2] == source_channel
            and transfer[3] == target_channel
        ):

            transfer_id = transfer[0]
            break

    await register_listener(
        client=tg_client,
        source_channel=source_channel,
        target_channel=target_channel,
        transfer_id=transfer_id,
    )
