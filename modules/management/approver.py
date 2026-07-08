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
        chat_id = event.chat_id
        await event.edit("🔄 **Initializing Join Request Engine...**")
        
        try:
            chat = await client.get_input_entity(chat_id)
            total_approved = 0
            
            while True:
                # Fetch requests batch
                res = await client(functions.messages.GetChatJoinRequestsRequest(
                    peer=chat,
                    limit=100
                ))
                
                if not res.requests:
                    break
                
                await event.edit(f"⏳ **Approving batch...** (Total: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        await client(functions.messages.HideChatJoinRequestRequest(
                            peer=chat,
                            user_id=req.user_id,
                            approved=True
                        ))
                        total_approved += 1
                        await asyncio.sleep(0.4)
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Limit Hit:** Sleeping {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except:
                        continue
                
                await asyncio.sleep(2)

            await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members in this chat.")
            
        except Exception as e:
            log.error(f"ApproveAll Error: {e}")
            await event.edit(f"❌ **Failed:** `{str(e)}` \n\nEnsure I am Admin with 'Add Members' rights.")

    # --- 2. TOGGLE AUTO-APPROVE (.autoapprove on/off) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve is now **{status}**.")

    # --- 3. UNIVERSAL RAW HANDLER (No-Crash Version) ---
    @client.on(events.Raw())
    async def raw_handler(update):
        """
        Catch any join request update without hardcoding the class name.
        Prevents load-time AttributeError.
        """
        # Check if the update is related to Chat Join Requests
        # Dono 'UpdateBotChatJoinRequest' aur 'UpdateChatJoinRequest' handle honge
        update_name = type(update).__name__
        
        if "ChatJoinRequest" in update_name:
            try:
                me = await client.get_me()
                # Database check if user enabled auto-approve
                if await get_approve_settings(me.id):
                    await client(functions.messages.HideChatJoinRequestRequest(
                        peer=update.peer,
                        user_id=update.user_id,
                        approved=True
                    ))
                    log.info(f"✅ Auto-approved user {update.user_id} in {update.peer}")
            except:
                pass
