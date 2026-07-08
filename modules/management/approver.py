import asyncio
import logging
from telethon import events, types, functions
# 🔥 Import fix: Specific functions ki jagah poora 'functions' module use karenge
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
            # Resolve the chat entity
            chat = await client.get_input_entity(chat_id)
            
            total_approved = 0
            while True:
                # 🔥 FIXED CALL: functions.messages format use kiya hai jo fail nahi hota
                res = await client(functions.messages.GetChatJoinRequestsRequest(
                    peer=chat,
                    limit=100
                ))
                
                if not res.requests:
                    break
                
                await event.edit(f"⏳ **Approving batch...** (Total so far: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        # 🔥 FIXED CALL: HideChatJoinRequestRequest
                        await client(functions.messages.HideChatJoinRequestRequest(
                            peer=chat,
                            user_id=req.user_id,
                            approved=True
                        ))
                        total_approved += 1
                        await asyncio.sleep(0.5) # Anti-Spam delay
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Telegram Limit:** Sleeping for {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except Exception as e:
                        continue
                
                # Batch gap
                await asyncio.sleep(2)

            await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members in this chat.")
            
        except Exception as e:
            log.error(f"ApproveAll Error: {e}")
            await event.edit(f"❌ **Failed:** `{str(e)}` \n\nCheck if Join Requests are active in this chat.")

    # --- 2. TOGGLE AUTO-APPROVE (.autoapprove on/off) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve is now **{status}**.")

    # --- 3. REAL-TIME AUTO APPROVER ---
    @client.on(events.Raw(types.UpdateBotChatJoinRequest))
    async def handler(update):
        try:
            me = await client.get_me()
            if await get_approve_settings(me.id):
                # 🔥 FIXED CALL: Auto-approver for new requests
                await client(functions.messages.HideChatJoinRequestRequest(
                    peer=update.peer,
                    user_id=update.user_id,
                    approved=True
                ))
        except Exception as e:
            log.debug(f"Auto-approve background fail: {e}")
