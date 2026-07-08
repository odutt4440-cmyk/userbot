import asyncio
import logging
from telethon import events, types, functions, __version__ as tv
from telethon.errors import FloodWaitError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

# --- 🔥 THE BINARY BYPASS (Constructor IDs) ---
# Ye IDs Telegram API ke core se li gayi hain. 
# Inhe kisi library version ki zaroorat nahi hoti.

class GetRequestsBinary(functions.TLRequest):
    CONSTRUCTOR_ID = 0xad6134f0
    SUBCLASS_OF_ID = 0x391f748a
    def __init__(self, peer, limit=100):
        self.peer = peer
        self.limit = limit
    def __bytes__(self):
        return b''.join([
            self.CONSTRUCTOR_ID.to_bytes(4, 'little'),
            self.peer.__bytes__(),
            self.limit.to_bytes(4, 'little'),
            b'\x00' * 12 # Padding for optional fields
        ])

class HideRequestBinary(functions.TLRequest):
    CONSTRUCTOR_ID = 0x7fe2e718
    SUBCLASS_OF_ID = 0xf5b3b9b
    def __init__(self, peer, user_id, approved=True):
        self.peer = peer
        self.user_id = user_id
        self.approved = approved
    def __bytes__(self):
        return b''.join([
            self.CONSTRUCTOR_ID.to_bytes(4, 'little'),
            b'\x01\x00\x00\x00' if self.approved else b'\x00\x00\x00\x00',
            self.peer.__bytes__(),
            self.user_id.__bytes__(),
        ])

def register(client):
    log.info(f"⚙️ Approver Module Loaded. Telethon Version in Runtime: {tv}")

    # --- 1. APPROVE ALL PENDING (.approveall) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Run this inside the group.")

        await event.edit(f"🔄 **Engine Booting...** (Library: v{tv})")
        chat_id = event.chat_id
        
        try:
            chat = await client.get_input_entity(chat_id)
            total_approved = 0
            
            while True:
                # 🔥 TRY 1: Standard Method
                try:
                    res = await client(functions.messages.GetChatJoinRequestsRequest(
                        peer=chat, limit=100
                    ))
                except AttributeError:
                    # 🔥 TRY 2: Binary Fallback if Library is too old
                    log.warning("Library outdated, using Binary Bypass...")
                    res = await client(GetRequestsBinary(peer=chat, limit=100))
                
                if not res or not hasattr(res, 'requests') or not res.requests:
                    break
                
                await event.edit(f"⏳ **Clearing Requests...** (Approved: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        try:
                            await client(functions.messages.HideChatJoinRequestRequest(
                                peer=chat, user_id=req.user_id, approved=True
                            ))
                        except AttributeError:
                            await client(HideRequestBinary(peer=chat, user_id=req.user_id, approved=True))
                        
                        total_approved += 1
                        await asyncio.sleep(0.4) 
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Limit:** Sleeping {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except:
                        continue
                
                await asyncio.sleep(1.5)

            if total_approved == 0:
                await event.edit("📭 **No requests found. Check Group Settings > Join Requests.**")
            else:
                await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members.")
            
        except Exception as e:
            log.error(f"Fatal Error: {repr(e)}")
            await event.edit(f"❌ **Error:** `{str(e)}` \n\nEnsure Userbot is OWNER/ADMIN.")

    # --- 2. TOGGLE AUTO-APPROVE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        await event.edit(f"🛡️ **Join Guard:** {'ENABLED ✅' if is_on else 'DISABLED 🛑'}")

    # --- 3. AUTO-APPROVER FOR NEW REQUESTS ---
    @client.on(events.Raw())
    async def raw_handler(update):
        if "ChatJoinRequest" in type(update).__name__:
            try:
                me = await client.get_me()
                if await get_approve_settings(me.id):
                    try:
                        await client(functions.messages.HideChatJoinRequestRequest(
                            peer=update.peer, user_id=update.user_id, approved=True
                        ))
                    except:
                        await client(HideRequestBinary(peer=update.peer, user_id=update.user_id, approved=True))
                    log.info(f"✅ Auto-approved {update.user_id}")
            except: pass
