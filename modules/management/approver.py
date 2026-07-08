import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

# --- 🔥 THE RAW PROTOCOL OVERRIDE (Jad se ilaaj) ---
# Ye classes seedha Telegram ke server se binary level par baat karti hain
# Library version koi bhi ho, ye 100% kaam karengi.

class GetRequests(functions.TLRequest):
    CONSTRUCTOR_ID = 0xad6134f0
    SUBCLASS_OF_ID = 0x391f748a
    def __init__(self, peer, limit=100):
        self.peer = peer
        self.limit = limit
    def to_dict(self): return {'_': 'GetChatJoinRequestsRequest', 'peer': self.peer, 'limit': self.limit}

class HideRequest(functions.TLRequest):
    CONSTRUCTOR_ID = 0x7fe2e718
    SUBCLASS_OF_ID = 0xf5b3b9b
    def __init__(self, peer, user_id, approved=True):
        self.peer = peer
        self.user_id = user_id
        self.approved = approved
    def to_dict(self): return {'_': 'HideChatJoinRequestRequest', 'peer': self.peer, 'user_id': self.user_id, 'approved': self.approved}

def register(client):

    # --- 1. APPROVE ALL PENDING ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Run this command INSIDE the group.")

        await event.edit("🔄 **Force Booting Join Request Engine...**")
        chat_id = event.chat_id
        
        try:
            chat = await client.get_input_entity(chat_id)
            total_approved = 0
            
            while True:
                # 🔥 RAW API CALL: No library attribute needed
                res = await client(GetRequests(peer=chat, limit=100))
                
                if not res or not hasattr(res, 'requests') or not res.requests:
                    break
                
                await event.edit(f"⏳ **Clearing Requests...** (Current: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        # 🔥 RAW API CALL: Approve
                        await client(HideRequest(peer=chat, user_id=req.user_id, approved=True))
                        total_approved += 1
                        await asyncio.sleep(0.4) 
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Limit:** Sleeping {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except:
                        continue
                
                await asyncio.sleep(1.5)

            if total_approved == 0:
                await event.edit("📭 **No requests found. Make sure I am Admin.**")
            else:
                await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members.")
            
        except Exception as e:
            log.error(f"Fatal Error: {repr(e)}")
            await event.edit(f"❌ **Fatal Error:** `{repr(e)}` \n\nEnsure Admin with 'Add Members' rights.")

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
                    # 🔥 RAW API CALL: Instant Approve
                    await client(HideRequest(peer=update.peer, user_id=update.user_id, approved=True))
                    log.info(f"✅ Auto-approved {update.user_id}")
            except:
                pass
