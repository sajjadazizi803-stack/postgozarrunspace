from telethon import TelegramClient, events
from telethon.tl import functions, types

import asyncio
import os

from database import (
    get_all_transfers,
    increase_sent_count,
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

        # -----------------------------------------
        # MEDIA
        # -----------------------------------------

        if message.media:

            file = await message.download_media()

            if not file:
                print(f"❌ Could not download message " f"{message.id}")

                return False

            try:

                await client.send_file(
                    entity=target_entity,
                    file=file,
                    caption=message.text or "",
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

            except Exception as e:

                print(f"❌ COUNT ERROR: {e}")

        print(f"✅ FORWARDED: " f"{message.id}")

        return True

    except Exception as e:

        print(f"❌ TRANSFER ERROR " f"{message.id}: " f"{type(e).name}: {e}")

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

        print(f"📌 CHANNEL PTS " f"{source_entity.id}: {pts}")

        return pts

    except Exception as e:

        print(f"❌ GET PTS ERROR " f"{source_entity.id}: " f"{type(e).name}: {e}")

        return None


# =========================================================
# CHANNEL DIFFERENCE POLLING
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

    print(f"🔄 CHANNEL POLLING STARTED: " f"{source_id} -> {target_id}")

    # =====================================================
    # INITIAL PTS
    # =====================================================

    pts = await get_channel_pts(
        client,
        source_entity,
    )

    if pts is None:

        print(f"❌ Could not initialize PTS " f"for {source_id}")

        polling_tasks.pop(
            transfer_key,
            None,
        )

        return

    channel_pts[transfer_key] = pts

    # =====================================================
    # LOOP
    # =====================================================

    try:

        while True:

            try:

                current_pts = channel_pts.get(
                    transfer_key,
                    pts,
                )

                result = await client(
                    functions.updates.GetChannelDifferenceRequest(
                        force=True,
                        channel=source_entity,
                        filter=types.ChannelMessagesFilterEmpty(),
                        pts=current_pts,
                        limit=100,
                    )
                )

                result_type = type(result).name

                # =================================================
                # NO NEW UPDATE
                # =================================================

                if result_type == "ChannelDifferenceEmpty":

                    channel_pts[transfer_key] = result.pts

                    pts = result.pts

                    await asyncio.sleep(2)

                    continue

                # =================================================
                # NEW UPDATES
                # =================================================

                if result_type == "ChannelDifference":

                    new_messages = result.new_messages or []

                    if new_messages:

                        print(f"📨 NEW CHANNEL MESSAGES: " f"{len(new_messages)}")

                    for message in sorted(
                        new_messages,
                        key=lambda x: x.id,
                    ):

                        last_id = last_messages.get(
                            transfer_key,
                            0,
                        )

                        # -----------------------------------------
                        # DUPLICATE PROTECTION
                        # -----------------------------------------

                        if message.id <= last_id:
                            continue

                        # -----------------------------------------
                        # REGISTER ID BEFORE SEND
                        # -----------------------------------------

                        last_messages[transfer_key] = message.id

                        await transfer_message(
                            client=client,
                            message=message,
                            target_entity=target_entity,
                            transfer_id=transfer_id,
                        )

                    # -----------------------------------------
                    # UPDATE PTS
                    # -----------------------------------------

                    channel_pts[transfer_key] = result.pts

                    pts = result.pts

                    # اگر هنوز ادامه دارد
                    if not getattr(
                        result,
                        "final",
                        True,
                    ):

                        await asyncio.sleep(0.1)

                        continue

                    await asyncio.sleep(2)

                    continue

                # =================================================
                # TOO LONG
                # =================================================

                if result_type == "ChannelDifferenceTooLong":

                    print(f"⚠️ CHANNEL DIFFERENCE " f"TOO LONG: " f"{source_id}")

                    # -----------------------------------------
                    # Reset PTS
                    # -----------------------------------------

                    new_pts = await get_channel_pts(
                        client,
                        source_entity,
                    )

                    if new_pts is not None:

                        channel_pts[transfer_key] = new_pts

                        pts = new_pts

                    await asyncio.sleep(2)

                    continue

                # =================================================
                # UNKNOWN RESPONSE
                # =================================================

                print(f"⚠️ UNKNOWN CHANNEL RESPONSE: " f"{result_type}")

                await asyncio.sleep(2)

            # =====================================================
            # FLOOD WAIT
            # =====================================================

            except Exception as e:

                print(
                    f"❌ CHANNEL POLLING ERROR " f"{source_id}: " f"{type(e).name}: {e}"
                )

                await asyncio.sleep(3)

    except asyncio.CancelledError:

        print(f"🛑 CHANNEL POLLING STOPPED: " f"{source_id}")

        raise

    finally:

        polling_tasks.pop(
            transfer_key,
            None,
        )


# =========================================================
# REGISTER LISTENER
# =========================================================


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

    # =====================================================
    # DUPLICATE LISTENER
    # =====================================================

    if key in registered_listeners:

        print(f"⚠️ ALREADY REGISTERED: " f"{source_channel} -> " f"{target_channel}")

        return

    # =====================================================
    # GET ENTITIES
    # =====================================================

    try:

        source_entity = await client.get_entity(source_channel)

        target_entity = await client.get_entity(target_channel)

        source_input = await client.get_input_entity(source_entity)

        target_input = await client.get_input_entity(target_entity)

        source_id = source_entity.id
        target_id = target_entity.id

        transfer_key = (
            source_id,
            target_id,
        )

    except Exception as e:

        print(f"❌ ENTITY ERROR: " f"{type(e).name}: {e}")

        return

    # =====================================================
    # EVENT
    # =====================================================

    async def new_post(event):

        try:

            message = event.message

            if not message:
                return

            message_id = message.id

            # -----------------------------------------
            # DUPLICATE CHECK
            # -----------------------------------------

            last_id = last_messages.get(
                transfer_key,
                0,
            )

            if message_id <= last_id:
                return

            # -----------------------------------------
            # SAVE ID
            # -----------------------------------------

            last_messages[transfer_key] = message_id

            print(f"📩 EVENT MESSAGE: " f"{message_id}")

            await transfer_message(
                client=client,
                message=message,
                target_entity=target_input,
                transfer_id=transfer_id,
            )

        except Exception as e:

            print(f"❌ EVENT ERROR: " f"{type(e).name}: {e}")

    # =====================================================
    # REGISTER EVENT WITH CHAT FILTER
    # =====================================================

    client.add_event_handler(
        new_post,
        events.NewMessage(chats=source_input),
    )

    event_handlers[transfer_key] = new_post

    # =====================================================
    # REGISTER LISTENER
    # =====================================================

    registered_listeners.add(key)

    # =====================================================
    # START ONLY ONE POLLER
    # =====================================================

    if transfer_key not in polling_tasks:

        task = asyncio.create_task(
            polling_worker(
                client=client,
                source_entity=source_entity,
                target_entity=target_input,
                transfer_id=transfer_id,
            )
        )

        polling_tasks[transfer_key] = task

    print(f"✅ LISTENER REGISTERED: " f"{source_channel} -> " f"{target_channel}")


# =========================================================
# START ALL LISTENERS
# =========================================================


async def start_all_listeners():

    if not tg_client.is_connected():

        await tg_client.connect()

    transfers = get_all_transfers()

    print(f"📋 TRANSFERS FOUND: " f"{len(transfers)}")

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

        print(f"🔗 STARTING: " f"{source} -> {target}")

        try:

            await register_listener(
                client=tg_client,
                source_channel=source,
                target_channel=target,
                transfer_id=transfer_id,
            )

        except Exception as e:

            print(
                f"❌ START LISTENER ERROR: "
                f"{source} -> {target}: "
                f"{type(e).name}: {e}"
            )


# =========================================================
# ADD NEW TRANSFER
# =========================================================


async def add_new_transfer(
    telegram_id,
    source_channel,
    target_channel,
):

    transfer_id = None

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
