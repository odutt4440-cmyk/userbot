from telethon import events
import time

# --- MODULE REGISTER ---
def register(client):

    # --- 1. ID COMMAND (.id) ---
    # Usage: .id (standalone) or .id (reply to user)
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.id'))
    async def get_id(event):
        # Reply mode
        if event.is_reply:
            reply = await event.get_reply_message()
            # reply.sender_id can sometimes be None in some channels, so we use from_id logic
            target_id = reply.sender_id
            await event.edit(
                f"👤 **𝐔sᴇʀ 𝐈𝐃:** `{target_id}`\n"
                f"👥 **𝐆ʀᴏᴜᴘ 𝐈𝐃:** `{event.chat_id}`"
            )
        else:
            # Standalone mode
            await event.edit(f"👥 **𝐂ʜᴧᴛ 𝐈𝐃:** `{event.chat_id}`")

    # --- 2. INFO COMMAND (.info) ---
    # Usage: .info (reply to user) or .info (self)
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.info'))
    async def get_info(event):
        status = await event.edit("🔍 **𝐅ᴇᴛᴄʜɪɴɢ ᴅᴇᴛᴧɪʟs...**")
        
        # Determine target
        if event.is_reply:
            reply = await event.get_reply_message()
            target = reply.sender_id
        else:
            target = "me" # Self info if no reply

        try:
            # Fetching the entity safely
            user = await client.get_entity(target)
            
            # Formatting Information
            first_name = user.first_name if user.first_name else "N/A"
            last_name = user.last_name if user.last_name else "N/A"
            username = f"@{user.username}" if user.username else "None"
            user_id = user.id
            is_bot = "Yes" if user.bot else "No"
            is_premium = "Yes" if getattr(user, 'premium', False) else "No"
            
            info_text = (
                "👤 **𝐔sᴇʀ 𝐈ɴꜰᴏʀᴍᴧᴛɪᴏɴ**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 **𝐅ɪʀsᴛ 𝐍ᴧᴍᴇ:** {first_name}\n"
                f"📝 **𝐋ᴧsᴛ 𝐍ᴧᴍᴇ:** {last_name}\n"
                f"🆔 **𝐔sᴇʀ 𝐈𝐃:** `{user_id}`\n"
                f"🔗 **𝐔sᴇʀɴᴧᴍᴇ:** {username}\n"
                f"🤖 **𝐁ᴏᴛ:** {is_bot}\n"
                f"💎 **𝐏ʀᴇᴍɪᴜᴍ:** {is_premium}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await status.edit(info_text)
            
        except Exception as e:
            # Error reporting
            await status.edit(f"❌ **𝐄ʀʀᴏʀ:** `{str(e)}` ")
