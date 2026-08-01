from telethon import TelegramClient, events

import config

from database import get_all_transfers

# =========================
# Global
# =========================

clients = {}
registered_listeners = set()


# =========================
# Register One Listener
# =========================


async def register_listener(
    client: TelegramClient,
    source_channel,
    target_channel,
):

    key = (
        client.session.filename,
        source_channel,
        target_channel,
    )

    if key in registered_listeners:
        print(f"⚠️ Listener already exists: {source_channel}")
        return

    try:

        source_entity = await client.get_input_entity(source_channel)
        target_entity = await client.get_input_entity(target_channel)

    except Exception as e:

        print(f"❌ Entity Error: {e}")
        return

    @client.on(events.NewMessage(chats=source_entity))
    async def new_post(event):

        try:

            message = event.message

            if message.media:

                file = await message.download_media()

                await client.send_file(
                    entity=target_entity,
                    file=file,
                    caption=message.text or "",
                )

            else:

                await client.send_message(
                    entity=target_entity,
                    message=message.text or "",
                )

            print(f"✅ Forwarded: {source_channel} -> {target_channel}")

        except Exception as e:

            print(f"❌ Forward Error: {e}")

    registered_listeners.add(key)

    print(f"✅ Listener Registered: {source_channel}")


# =========================
# Start All Listeners
# =========================


async def start_all_listeners():

    print("========== start_all_listeners ==========")

    transfers = get_all_transfers()

    print("Transfers:", transfers)

    for transfer in transfers:

        print("Transfer Row:", transfer)

        telegram_id = transfer[0]
        source = transfer[1]
        target = transfer[2]
        enabled = transfer[3]

        if enabled != 1:
            continue

        session_name = f"sessions/{telegram_id}"

        if telegram_id not in clients:

            try:
                client = TelegramClient(
                    session_name,
                    config.API_ID,
                    config.API_HASH,
                )

                await client.start()

                clients[telegram_id] = client

            except Exception as e:
                print(f"❌ Client start error for {telegram_id}: {e}")
                continue  # <-- این خط اضافه شده

        client = clients[telegram_id]

        await register_listener(
            client,
            source,
            target,
        )

    print("✅ All Listeners Started.")


# ----------------- add new transfer -----------------


async def add_new_transfer(telegram_id, source_channel, target_channel):
    """ثبت لیسنر برای انتقال جدید بدون نیاز به ری‌استارت"""

    session_name = f"sessions/{telegram_id}"

    # اگر کلاینت وجود نداشت، ایجاد کن
    if telegram_id not in clients:
        client = TelegramClient(
            session_name,
            config.API_ID,
            config.API_HASH,
        )
        await client.start()
        clients[telegram_id] = client

    client = clients[telegram_id]

    # ثبت لیسنر جدید
    await register_listener(
        client,
        source_channel,
        target_channel,
    )

    print(f"✅ New listener added: {source_channel} -> {target_channel}")
