import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # --- 1. APPROVE ALL PENDING (.approveall) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        await event.edit("🔄 **Searching for Join Requests...**")
        chat_id = event.chat_id
        
        try:
            # 1. Get Chat Entity
            chat = await client.get_entity(chat_id)
            total_approved = 0
            
            while True:
                # 2. Fetch Requests using the most stable path
                try:
                    res = await client(functions.messages.GetChatJoinRequestsRequest(
                        peer=chat,
                        limit=100
                    ))
                except Exception as api_err:
                    log.error(f"API Fetch Error: {api_err}")
                    return await event.edit(f"❌ **API Error:** `{repr(api_err)}` \n\nCheck if 'Join Requests' are actually pending.")

                if not res or not res.requests:
                    break
                
                await event.edit(f"⏳ **Batch Processing...** (Total: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        # 3. Hide/Approve Request
                        await client(functions.messages.HideChatJoinRequestRequest(
                            peer=chat,
                            user_id=req.user_id,
                            approved=True
                        ))
                        total_approved += 1
                        await asyncio.sleep(0.3) # Faster but safe
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Telegram Limit:** Sleeping {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except:
                        continue
                
                await asyncio.sleep(1.5)

            if total_approved == 0:
                await event.edit("📭 **No pending join requests found in this chat.**")
            else:
                await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members.")
            
        except Exception as e:
            # 🔥 REPR use kiya hai taaki khali error na aaye
            error_details = repr(e)
            log.error(f"ApproveAll Fatal Error: {error_details}")
            await event.edit(f"❌ **Fatal Error:** `{error_details}`")

    # --- 2. TOGGLE AUTO-APPROVE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve is now **{status}**.")

    # --- 3. RAW HANDLER FOR NEW REQUESTS ---
    @client.on(events.Raw())
    async def raw_handler(update):
        update_name = type(update).__name__
        if "ChatJoinRequest" in update_name:
            try:
                me = await client.get_me()
                if await get_approve_settings(me.id):
                    await client(functions.messages.HideChatJoinRequestRequest(
                        peer=update.peer,
                        user_id=update.user_id,
                        approved=True
                    ))
                    log.info(f"✅ Auto-approved {update.user_id}")
            except:
                pass
