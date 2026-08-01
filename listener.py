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

        try:

            source_entity = await client.get_entity(source)

            @client.on(events.NewMessage(chats=source_entity))
            async def new_post(event, target=target):

                try:

                    if event.message.media:

                        file = await event.message.download_media()

                        await client.send_file(
                            target,
                            file=file,
                            caption=event.message.text or "",
                        )

                    else:

                        await client.send_message(
                            target,
                            event.message.text or "",
                        )

                    print(f"✅ {source} -> {target}")

                except Exception as e:

                    print(f"❌ Forward Error: {e}")

            print(f"✅ Listener registered: {source}")

        except Exception as e:

            print(f"❌ Listener register failed: {e}")

    print("✅ Listeners Started.")


# ----------------- register listeners --------------


from telethon import events


def register_listener(client, source_channel, target_channel):

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

            print(f"✅ Forwarded: {source_channel} -> {target_channel}")

        except Exception as e:

            print(f"❌ Forward Error: {e}")

    async def setup():

        try:

            source_entity = await client.get_entity(source_channel)

            client.add_event_handler(
                new_post,
                events.NewMessage(chats=source_entity),
            )

            print(f"✅ Listener registered: {source_channel}")

        except Exception as e:

            print(f"❌ Listener register failed: {e}")

    client.loop.create_task(setup())
