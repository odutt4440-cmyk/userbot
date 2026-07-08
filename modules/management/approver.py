import asyncio
import logging
from telethon import events, types, functions
from telethon.tl.functions.messages import GetChatJoinRequestsRequest, HideChatJoinRequestRequest
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
            # 1. Resolve the chat entity properly
            chat = await client.get_input_entity(chat_id)
            
            total_approved = 0
            while True:
                # 2. Fetch Join Requests (Batch of 100)
                # Offset use kar rahe hain taaki pagination sahi chale
                res = await client(GetChatJoinRequestsRequest(
                    peer=chat,
                    limit=100
                ))
                
                if not res.requests:
                    break
                
                await event.edit(f"⏳ **Approving batch...** (Current: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        # 3. Approve the User
                        await client(HideChatJoinRequestRequest(
                            peer=chat,
                            user_id=req.user_id,
                            approved=True
                        ))
                        total_approved += 1
                        # Fast processing but safe
                        await asyncio.sleep(0.4) 
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **FloodWait:** Sleeping for {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except Exception as e:
                        log.error(f"Approval error: {e}")
                        continue
                
                # Chota gap batches ke beech me
                await asyncio.sleep(2)

            await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members in this chat.")
            
        except Exception as e:
            await event.edit(f"❌ **Failed:** `{str(e)}` \n\n**Reasons:**\n1. I might not be Admin.\n2. This chat doesn't have 'Join Requests' enabled.\n3. Telethon Peer Mismatch.")

    # --- 2. TOGGLE AUTO-APPROVE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Auto-Approve status:** {status}")

    # --- 3. REAL-TIME AUTO APPROVER ---
    @client.on(events.Raw(types.UpdateBotChatJoinRequest))
    async def handler(update):
        try:
            me = await client.get_me()
            if await get_approve_settings(me.id):
                await client(HideChatJoinRequestRequest(
                    peer=update.peer,
                    user_id=update.user_id,
                    approved=True
                ))
        except:
            pass
