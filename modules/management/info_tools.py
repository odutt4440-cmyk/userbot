import asyncio
from telethon import events
from telethon.utils import get_peer_id

# --- MODULE REGISTER ---
def register(client):

    # --- 1. ID COMMAND (.id) ---
    # Har chat me kaam karega (Groups, Channels, DMs)
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.id'))
    async def get_id(event):
        try:
            # Current Chat ID nikalna
            chat_id = event.chat_id
            
            if event.is_reply:
                reply = await event.get_reply_message()
                # Reply wale bande ki ID
                user_id = reply.sender_id
                await event.edit(
                    f"👤 **𝐔sᴇʀ 𝐈𝐃:** `{user_id}`\n"
                    f"👥 **𝐂ʜᴧᴛ 𝐈𝐃:** `{chat_id}`"
                )
            else:
                # Sirf Chat ID
                await event.edit(f"👥 **𝐂ʜᴧᴛ 𝐈𝐃:** `{chat_id}`")
        except Exception as e:
            print(f"ID Error: {e}")

    # --- 2. INFO COMMAND (.info) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.info'))
    async def get_info(event):
        # Processing message bhejenge taaki pta chale bot zinda hai
        status = await event.edit("🔍 **𝐒ᴄᴧɴɴɪɴɢ 𝐃ᴇᴛᴧɪʟs...**")
        
        try:
            if event.is_reply:
                reply = await event.get_reply_message()
                target = await client.get_entity(reply.sender_id)
            else:
                # Agar reply nahi hai toh apni info ya chat info
                target = await client.get_entity(event.chat_id)

            # Formatting
            first_name = getattr(target, 'first_name', "N/A")
            last_name = getattr(target, 'last_name', "N/A")
            username = f"@{target.username}" if getattr(target, 'username', None) else "None"
            uid = target.id
            
            # Additional Flags
            is_bot = "Yes" if getattr(target, 'bot', False) else "No"
            is_premium = "Yes" if getattr(target, 'premium', False) else "No"
            is_scam = "Yes" if getattr(target, 'scam', False) else "No"

            info_text = (
                "👤 **𝐔sᴇʀ / 𝐂ʜᴧᴛ 𝐈ɴꜰᴏ**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 **𝐍ᴧᴍᴇ:** {first_name} {last_name if last_name != 'N/A' else ''}\n"
                f"🆔 **𝐈𝐃:** `{uid}`\n"
                f"🔗 **𝐔sᴇʀɴᴧᴍᴇ:** {username}\n"
                f"🤖 **𝐁ᴏᴛ:** {is_bot}\n"
                f"💎 **𝐏ʀᴇᴍɪᴜᴍ:** {is_premium}\n"
                f"🚫 **𝐒ᴄᴧᴍ:** {is_scam}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            await status.edit(info_text)
            
        except Exception as e:
            await status.edit(f"❌ **𝐄ʀʀᴏʀ:** `{str(e)}` ")
            # 5 second baad error delete karo taaki chat saaf rahe
            await asyncio.sleep(5)
            await status.delete()
