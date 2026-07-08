import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # --- 1. APPROVE ALL PENDING ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Run this command INSIDE the group.")

        await event.edit("🔄 **Force Booting Join Request Engine...**")
        chat_id = event.chat_id
        
        try:
            # 1. Resolve Chat
            chat = await client.get_input_entity(chat_id)
            total_approved = 0
            
            # 🔥 THE SEARCH LOGIC: Telethon ke alag versions me alag naam ho sakte hain
            # Hum saare possible names try karenge
            GetReq = getattr(functions.messages, 'GetChatJoinRequestsRequest', 
                     getattr(functions.messages, 'GetChatJoinRequests', None))
            
            HideReq = getattr(functions.messages, 'HideChatJoinRequestRequest', 
                      getattr(functions.messages, 'HideChatJoinRequest', None))

            if not GetReq:
                return await event.edit("❌ **Fatal:** Your Telethon version is strictly blocking this feature. Please 'Restart' Railway Service (not just redeploy).")

            while True:
                # 2. Fetch Requests
                try:
                    res = await client(GetReq(peer=chat, limit=100))
                except Exception as api_e:
                    log.error(f"Fetch Fail: {api_e}")
                    break
                
                if not res or not hasattr(res, 'requests') or not res.requests:
                    break
                
                await event.edit(f"⏳ **Clearing Requests...** (Approved: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        # 3. Approve User
                        await client(HideReq(peer=chat, user_id=req.user_id, approved=True))
                        total_approved += 1
                        await asyncio.sleep(0.4) 
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Limit:** Sleeping {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except:
                        continue
                
                await asyncio.sleep(1.5)

            if total_approved == 0:
                await event.edit("📭 **No requests found. Check if requests are pending in Group Settings.**")
            else:
                await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members.")
            
        except Exception as e:
            log.error(f"Fatal Error: {repr(e)}")
            await event.edit(f"❌ **Error:** `{repr(e)}` \n\nMake sure I have 'Invite Users' admin power.")

    # --- 2. TOGGLE AUTO-APPROVE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve is now **{status}**.")

    # --- 3. AUTO-APPROVER FOR NEW REQUESTS ---
    @client.on(events.Raw())
    async def raw_handler(update):
        update_name = type(update).__name__
        if "ChatJoinRequest" in update_name:
            try:
                me = await client.get_me()
                if await get_approve_settings(me.id):
                    HideReq = getattr(functions.messages, 'HideChatJoinRequestRequest', 
                              getattr(functions.messages, 'HideChatJoinRequest', None))
                    if HideReq:
                        await client(HideReq(peer=update.peer, user_id=update.user_id, approved=True))
                        log.info(f"✅ Auto-approved {update.user_id}")
            except:
                pass
