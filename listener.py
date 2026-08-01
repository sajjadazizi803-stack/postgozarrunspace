from telethon import TelegramClient, events

import config

from database import (
    get_all_transfers,
)

clients = {}

# =========================
# start all listeners
# =========================


async def start_all_listeners():

    transfers = get_all_transfers()

    for transfer in transfers:

        telegram_id = transfer[0]
        source = transfer[1]
        target = transfer[2]
        enabled = transfer[3]

        if enabled != 1:
            continue

        session_name = f"sessions/{telegram_id}"

        if telegram_id not in clients:

            client = TelegramClient(
                session_name,
                config.API_ID,
                config.API_HASH,
            )

            await client.start()

            clients[telegram_id] = client

        client = clients[telegram_id]

        register_listener(
            client,
            source,
            target,
        )

    print("✅ Listeners Started.")


# ----------------- register start all listeners --------------


def register_listener(client, source_channel, target_channel):

    @client.on(events.NewMessage(chats=source_channel))
    async def new_post(event):

        message = event.message

        try:

            if message.media:

                file = await message.download_media()

                await client.send_file(
                    target_channel,
                    file=file,
                    caption=message.text or "",
                )

            else:

                await client.send_message(
                    target_channel,
                    message.text or "",
                )

            print(f"✅ {source_channel} -> {target_channel}")

        except Exception as e:

            print(e)
