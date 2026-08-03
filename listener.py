from telethon import TelegramClient, events
from telethon.tl import functions, types

import asyncio
import os

from database import (
    get_all_transfers,
    increase_sent_count,
    get_remove_last_lines,
    get_append_last_lines,
)

from telegram_client import tg_client

# =========================================================
# GLOBAL
# =========================================================

registered_listeners = set()

event_handlers = {}

polling_tasks = {}

last_messages = {}

channel_pts = {}


# ------------------- stop transfer listener --------------------


async def stop_transfer_listener(
    source_channel,
    target_channel,
):
    try:

        source_entity = await tg_client.get_entity(source_channel)
        target_entity = await tg_client.get_entity(target_channel)

        key = (
            source_entity.id,
            target_entity.id,
        )

        task = polling_tasks.pop(key, None)

        if task:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        # پاک کردن event listener
        handler = event_handlers.pop(key, None)

        if handler:
            try:
                tg_client.remove_event_handler(handler)
            except Exception:
                pass

        registered_listeners.discard(key)

        last_messages.pop(key, None)
        channel_pts.pop(key, None)

        print(f"🛑 LISTENER STOPPED: {source_channel} -> {target_channel}")

        return True

    except Exception as e:

        print(
            "❌ STOP LISTENER ERROR:",
            type(e).__name__,
            str(e),
        )

        return False


# ------------------- remove last lines --------------------


def remove_last_lines(text, count):

    if not text or count <= 0:
        return text

    lines = text.splitlines()

    if len(lines) <= count:
        return ""

    return "\n".join(lines[:-count])


# ------------------- append last lines --------------------


def append_last_lines(text, append_text):

    if not append_text:
        return text

    if not text:
        return append_text

    return text + "\n\n" + append_text


# =========================================================
# TRANSFER MESSAGE
# =========================================================


async def transfer_message(
    client: TelegramClient,
    message,
    target_entity,
    transfer_id=None,
):

    try:

        remove_count = 0
        append_text = ""

        if transfer_id is not None:

            try:
                remove_count = get_remove_last_lines(transfer_id)
            except Exception:
                remove_count = 0

            try:
                append_text = get_append_last_lines(transfer_id)
            except Exception:
                append_text = ""

        # -----------------------------------------
        # MEDIA
        # -----------------------------------------

        if message.media:

            file = await message.download_media()

            if not file:
                return False

            try:

                caption = message.text or ""

                if remove_count > 0:
                    caption = remove_last_lines(caption, remove_count)

                if append_text:
                    caption = append_last_lines(caption, append_text)

                await client.send_file(
                    entity=target_entity,
                    file=file,
                    caption=caption,
                )

            finally:

                try:
                    if os.path.exists(file):
                        os.remove(file)

                except Exception:
                    pass

        # -----------------------------------------
        # TEXT
        # -----------------------------------------

        else:

            text = message.text or ""

            if not text:
                return False

            if remove_count > 0:
                text = remove_last_lines(text, remove_count)

            if append_text:
                text = append_last_lines(text, append_text)

            if not text:
                return False

            await client.send_message(
                entity=target_entity,
                message=text,
            )

        # -----------------------------------------
        # DATABASE
        # -----------------------------------------

        if transfer_id is not None:

            try:
                increase_sent_count(transfer_id)

            except Exception:
                pass

        return True

    except Exception as e:

        print("TRANSFER ERROR:", e)

        return False


# =========================================================
# GET CHANNEL PTS
# =========================================================


async def get_channel_pts(
    client: TelegramClient,
    source_entity,
):

    try:

        result = await client(
            functions.channels.GetFullChannelRequest(channel=source_entity)
        )

        pts = result.full_chat.pts

        return pts

    except Exception as e:

        return None


# =========================================================
# polling worker
# =========================================================


async def polling_worker(
    client: TelegramClient,
    source_entity,
    target_entity,
    transfer_id=None,
):
    source_id = source_entity.id
    target_id = target_entity.id

    transfer_key = (
        source_id,
        target_id,
    )

    while True:

        try:

            # بررسی وضعیت انتقال
            transfers = get_all_transfers()

            enabled = False

            for transfer in transfers:
                if transfer[0] == transfer_id:
                    enabled = transfer[4] == 1
                    break

            # اگر انتقال متوقف شده بود
            if not enabled:
                await asyncio.sleep(3)
                continue

            messages = await client.get_messages(
                source_entity,
                limit=1,
            )

            if not messages:
                await asyncio.sleep(2)
                continue

            message = messages[0]

            last_id = last_messages.get(
                transfer_key,
                0,
            )

            if message.id > last_id:

                last_messages[transfer_key] = message.id

                await transfer_message(
                    client=client,
                    message=message,
                    target_entity=target_entity,
                    transfer_id=transfer_id,
                )

            await asyncio.sleep(2)

        except Exception:

            await asyncio.sleep(5)


# -------------------- register listener -----------------


async def register_listener(
    client: TelegramClient,
    source_channel,
    target_channel,
    transfer_id=None,
):

    source_entity = await client.get_entity(source_channel)

    target_entity = await client.get_entity(target_channel)

    transfer_key = (
        source_entity.id,
        target_entity.id,
    )

    if transfer_key in polling_tasks:
        return

    task = asyncio.create_task(
        polling_worker(
            client=client,
            source_entity=source_entity,
            target_entity=target_entity,
            transfer_id=transfer_id,
        )
    )

    polling_tasks[transfer_key] = task


# =========================================================
# START ALL LISTENERS
# =========================================================


async def start_all_listeners():

    if not tg_client.is_connected():

        await tg_client.connect()

    transfers = get_all_transfers()

    for transfer in transfers:

        # IMPORTANT:
        #
        # database returns:
        #
        # id,
        # telegram_id,
        # source_channel,
        # target_channel,
        # enabled

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

        except Exception:
            pass


# =========================================================
# ADD NEW TRANSFER
# =========================================================


async def add_new_transfer(
    telegram_id,
    source_channel,
    target_channel,
):

    transfer_id = None

    source_entity = await tg_client.get_entity(source_channel)
    target_entity = await tg_client.get_entity(target_channel)

    key = (
        source_entity.id,
        target_entity.id,
    )

    if key in polling_tasks or key in registered_listeners:
        print(f"⚠️ LISTENER ALREADY EXISTS: {source_channel} -> {target_channel}")
        return

    # -----------------------------------------------------
    # پیدا کردن ID انتقال تازه ثبت شده
    # -----------------------------------------------------

    transfers = get_all_transfers()

    for transfer in transfers:

        if (
            transfer[1] == telegram_id
            and transfer[2] == source_channel
            and transfer[3] == target_channel
            and transfer[4] == 1
        ):

            transfer_id = transfer[0]

            break

    # -----------------------------------------------------
    # Register
    # -----------------------------------------------------

    await register_listener(
        client=tg_client,
        source_channel=source_channel,
        target_channel=target_channel,
        transfer_id=transfer_id,
    )
