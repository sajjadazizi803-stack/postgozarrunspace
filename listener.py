from telethon import TelegramClient, events
import os
import config
from database import get_all_transfers
from telegram_client import tg_client

# =========================
# Global
# =========================

registered_listeners = set()
os.makedirs("/tmp/sessions/", exist_ok=True)

# =========================
# Register One Listener
# =========================


async def register_listener(
    client: TelegramClient,
    source_channel,
    target_channel,
):

    key = (
        source_channel,
        target_channel,
    )

    if key in registered_listeners:
        return

    try:

        source_entity = await client.get_entity(source_channel)
        target_entity = await client.get_entity(target_channel)

        source_id = source_entity.id

    except Exception as e:
        print("REGISTER ERROR:", e)
        return

    @client.on(events.NewMessage)
    async def new_post(event):

        print("📩 NEW MESSAGE:", event.chat_id)

        try:

            if event.chat.id != source_id:
                return

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

        except Exception as e:
            print("TRANSFER ERROR:", e)

    print(f"✅ Listener Registered: {source_channel} -> {target_channel}")

    registered_listeners.add(key)


# =========================
# Start All Listeners
# =========================


async def start_all_listeners():

    if not tg_client.is_connected():
        await tg_client.connect()

    transfers = get_all_transfers()

    for transfer in transfers:

        telegram_id = transfer[0]
        source = transfer[1]
        target = transfer[2]
        enabled = transfer[3]

        if enabled != 1:
            continue

        client = tg_client

        await register_listener(
            client,
            source,
            target,
        )


# ----------------- add new transfer -----------------


async def add_new_transfer(telegram_id, source_channel, target_channel):
    """ثبت لیسنر برای انتقال جدید بدون نیاز به ری‌استارت"""

    client = tg_client

    await register_listener(
        client,
        source_channel,
        target_channel,
    )
