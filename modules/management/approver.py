import asyncio
import logging
from telethon import events, types, functions
from telethon.tl.functions.messages import GetChatJoinRequestsRequest, HideChatJoinRequestRequest
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # --- 1. APPROVE ALL PENDING (.approveall) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        chat_id = event.chat_id
        await event.edit("🔍 **Scanning for pending join requests...**")
        
        count = 0
        try:
            while True:
                # Fetch batch of 100 requests
                requests = await client(GetChatJoinRequestsRequest(
                    peer=chat_id,
                    limit=100
                ))
                
                if not requests.requests:
                    break
                
                for req in requests.requests:
                    try:
                        await client(HideChatJoinRequestRequest(
                            peer=chat_id,
                            user_id=req.user_id,
                            approved=True # True means ACCEPT
                        ))
                        count += 1
                        # Anti-Flood Wait: Small gap every 5 approvals
                        if count % 5 == 0:
                            await asyncio.sleep(1.5)
                    except Exception as e:
                        log.error(f"Approval failed for {req.user_id}: {e}")
                        continue
                
                # Big gap between batches
                await asyncio.sleep(3)

            await event.respond(f"✅ **Task Finished!**\nSuccessfully approved `{count}` members in this chat.")
        except Exception as e:
            await event.edit(f"❌ **Error:** `{str(e)}` \nEnsure I have 'Add Members' admin rights.")

    # --- 2. TOGGLE AUTO-APPROVE (.autoapprove on/off) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        user_id = event.sender_id
        is_on = (mode == "on")
        
        await set_approve_settings(user_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve for new members is now **{status}**.")

    # --- 3. BACKGROUND LISTENER (Real-time) ---
    @client.on(events.Raw(types.UpdateBotChatJoinRequest))
    async def handler(update):
        # Manager se status check karo (Iske liye client.me.id use hota hai)
        me = await client.get_me()
        is_enabled = await get_approve_settings(me.id)
        
        if not is_enabled:
            return

        try:
            await client(HideChatJoinRequestRequest(
                peer=update.peer,
                user_id=update.user_id,
                approved=True
            ))
        except:
            pass
