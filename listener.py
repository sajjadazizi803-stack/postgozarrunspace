from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityCustomEmoji
from telethon.tl import functions, types
from telethon.sessions import StringSession
from database import get_account

import asyncio
import os

from database import (
    get_all_transfers,
    increase_sent_count,
    get_remove_last_lines,
    get_append_last_lines,
)

from telegram_client import tg_client
from telethon.tl.types import InputSingleMedia

# =========================================================
# GLOBAL
# =========================================================

registered_listeners = set()

event_handlers = {}

polling_tasks = {}

last_messages = {}

channel_pts = {}


# ------------------- get transfer client --------------------


async def get_transfer_client(
    telegram_id,
    account_type,
):
    """
    مشخص می‌کند انتقال با کدام اکانت انجام شود.

    bot  -> tg_client
    user -> Session همان کاربر
    """

    if account_type == "bot":
        return tg_client, False

    account = get_account(telegram_id)

    if not account:
        raise RuntimeError("اکانت کاربر پیدا نشد.")

    api_id = account[1]
    api_hash = account[2]
    session_string = account[4]

    if not api_id or not api_hash or not session_string:
        raise RuntimeError("اطلاعات Session اکانت کاربر کامل نیست.")

    client = TelegramClient(
        StringSession(session_string),
        int(api_id),
        api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():

        await client.disconnect()

        raise RuntimeError("Session اکانت کاربر معتبر نیست.")

    return client, True


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

        return True

    except Exception as e:

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
        # ALBUM
        # -----------------------------------------

        if message.grouped_id:

            album = []

            async for m in client.iter_messages(
                message.chat_id,
                limit=20,
            ):

                if m.grouped_id == message.grouped_id:
                    album.append(m)

                elif album:
                    break

            album.reverse()

            if not album:
                album = [message]

            files = [m.media for m in album]

            caption = album[0].text or ""
            entities = album[0].entities

            if remove_count > 0:
                caption = remove_last_lines(
                    caption,
                    remove_count,
                )

            if append_text:
                caption = append_last_lines(
                    caption,
                    append_text,
                )

            await client.send_file(
                entity=target_entity,
                file=files,
                caption=caption,
                formatting_entities=entities,
            )

            return True

        # -----------------------------------------
        # MEDIA
        # -----------------------------------------

        if message.media:

            caption = message.text or ""

            if remove_count > 0:
                caption = remove_last_lines(
                    caption,
                    remove_count,
                )

            if append_text:
                caption = append_last_lines(
                    caption,
                    append_text,
                )

            await client.send_file(
                entity=target_entity,
                file=message.media,
                caption=caption,
                formatting_entities=message.entities,
            )

            return True

        # -----------------------------------------
        # TEXT
        # -----------------------------------------

        else:

            text = message.text or ""

            if not text:
                return False

            if remove_count > 0:
                text = remove_last_lines(
                    text,
                    remove_count,
                )

            if append_text:
                text = append_last_lines(text, append_text)

            if not text:
                return False

            await client.send_message(
                entity=target_entity,
                message=text,
                formatting_entities=message.entities,
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
    transfer_key = transfer_id

    while True:

        try:

            transfers = get_all_transfers()

            transfer = None

            for item in transfers:

                if item[0] == transfer_id:
                    transfer = item
                    break

            if not transfer:

                await asyncio.sleep(3)
                continue

            enabled = transfer[4] == 1

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

            messages.reverse()

            for message in messages:

                last_id = last_messages.get(
                    transfer_key,
                    0,
                )

                if message.id <= last_id:
                    continue

                if message.grouped_id:

                    grouped_ids = [
                        m.id for m in messages if m.grouped_id == message.grouped_id
                    ]

                    if grouped_ids:

                        if message.id != max(grouped_ids):
                            continue

                last_messages[transfer_key] = message.id

                await transfer_message(
                    client=client,
                    message=message,
                    target_entity=target_entity,
                    transfer_id=transfer_id,
                )

            await asyncio.sleep(2)

        except asyncio.CancelledError:

            break

        except Exception as e:

            print(
                f"[TRANSFER {transfer_id} ERROR]",
                e,
            )

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

    # هر انتقال Listener مستقل خودش را دارد
    transfer_key = transfer_id

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

    registered_listeners.add(transfer_key)

    print(
        f"[LISTENER STARTED] "
        f"transfer={transfer_id} "
        f"source={source_channel} "
        f"target={target_channel}"
    )


# =========================================================
# START ALL LISTENERS
# =========================================================


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

        account_type = transfer[5]

        if enabled != 1:
            continue

        client = None
        should_disconnect = False

        try:

            client, should_disconnect = await get_transfer_client(
                telegram_id,
                account_type,
            )

            await register_listener(
                client=client,
                source_channel=source,
                target_channel=target,
                transfer_id=transfer_id,
            )

            print(f"[TRANSFER RESTORED] " f"id={transfer_id} " f"type={account_type}")

        except Exception as e:

            print(
                f"[TRANSFER RESTORE ERROR] " f"id={transfer_id}:",
                e,
            )

            if should_disconnect and client:

                try:
                    await client.disconnect()
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
    account_type = "bot"

    transfers = get_all_transfers()

    for transfer in transfers:

        if (
            transfer[1] == telegram_id
            and transfer[2] == source_channel
            and transfer[3] == target_channel
            and transfer[4] == 1
        ):

            transfer_id = transfer[0]
            account_type = transfer[5] or "bot"

            break

    if transfer_id is None:

        print("[ADD LISTENER] transfer not found")
        return

    try:

        client, should_disconnect = await get_transfer_client(
            telegram_id,
            account_type,
        )

        await register_listener(
            client=client,
            source_channel=source_channel,
            target_channel=target_channel,
            transfer_id=transfer_id,
        )

        print(f"[ADD LISTENER] " f"id={transfer_id} " f"type={account_type}")

    except Exception as e:

        print(
            f"[ADD LISTENER ERROR] " f"id={transfer_id}:",
            e,
        )
