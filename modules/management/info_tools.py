from telethon import events

def register(client):
    # --- 1. ID (.id) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.id$'))
    async def get_id(event):
        if event.is_reply:
            reply = await event.get_reply_message()
            await event.edit(f"👤 **User ID:** `{reply.sender_id}`\n👥 **Group ID:** `{event.chat_id}`")
        else:
            await event.edit(f"👥 **Chat ID:** `{event.chat_id}`")

    # --- 2. INFO (.info) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.info$'))
    async def get_info(event):
        status = await event.edit("🔍 **Fetching user details...**")
        target = event.sender_id
        if event.is_reply:
            reply = await event.get_reply_message()
            target = reply.sender_id
        
        try:
            user = await client.get_entity(target)
            info = (
                "👤 **User Information**\n\n"
                f"**First Name:** {user.first_name}\n"
                f"**Last Name:** {user.last_name if user.last_name else 'N/A'}\n"
                f"**User ID:** `{user.id}`\n"
                f"**Username:** @{user.username if user.username else 'N/A'}\n"
                f"**Bot:** {'Yes' if user.bot else 'No'}\n"
                f"**Premium:** {'Yes' if user.premium else 'No'}"
            )
            await status.edit(info)
        except Exception as e:
            await status.edit(f"❌ **Error:** `{e}`")
