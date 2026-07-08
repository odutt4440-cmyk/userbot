import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

# --- 🔥 THE RAW CONSTRUCTOR LOGIC (SaaS Level Hack) ---
# Agar library me functions missing hain, toh hum manually define kar rahe hain
class CustomGetRequests(functions.TLRequest):
    CONSTRUCTOR_ID = 0xad6134f0
    SUBCLASS_OF_ID = 0x391f748a
    def __init__(self, peer, limit=100, invitelink=None, q=None, offset_date=None, offset_user=None):
        self.peer = peer
        self.limit = limit
        self.invitelink = invitelink
        self.q = q
        self.offset_date = offset_date
        self.offset_user = offset_user
    def to_dict(self): return {'_': 'GetChatJoinRequestsRequest', 'peer': self.peer, 'limit': self.limit}

class CustomHideRequest(functions.TLRequest):
    CONSTRUCTOR_ID = 0x7fe2e718
    SUBCLASS_OF_ID = 0xf5b3b9b
    def __init__(self, peer, user_id, approved=True):
        self.peer = peer
        self.user_id = user_id
        self.approved = approved
    def to_dict(self): return {'_': 'HideChatJoinRequestRequest', 'peer': self.peer, 'user_id': self.user_id, 'approved': self.approved}

def register(client):

    # --- 1. APPROVE ALL PENDING (.approveall) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        chat_id = event.chat_id
        # Saved Messages me test kar rahe ho toh stop karo
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group where requests are pending.")

        await event.edit("🔄 **Initializing Join Request Engine (Hybrid Mode)...**")
        
        try:
            chat = await client.get_input_entity(chat_id)
            total_approved = 0
            
            while True:
                # 🔥 Dynamic Discovery: Pehle library check, fir Custom fallback
                try:
                    req_call = functions.messages.GetChatJoinRequestsRequest(peer=chat, limit=100)
                except AttributeError:
                    req_call = CustomGetRequests(peer=chat, limit=100)

                res = await client(req_call)
                
                if not res or not res.requests:
                    break
                
                await event.edit(f"⏳ **Approving batch...** (Total: `{total_approved}`)")
                
                for req in res.requests:
                    try:
                        # 🔥 Dynamic Approval Call
                        try:
                            hide_call = functions.messages.HideChatJoinRequestRequest(peer=chat, user_id=req.user_id, approved=True)
                        except AttributeError:
                            hide_call = CustomHideRequest(peer=chat, user_id=req.user_id, approved=True)
                            
                        await client(hide_call)
                        total_approved += 1
                        await asyncio.sleep(0.5) 
                        
                    except FloodWaitError as f:
                        await event.respond(f"⚠️ **Telegram Limit:** Sleeping {f.seconds}s...")
                        await asyncio.sleep(f.seconds)
                    except:
                        continue
                
                await asyncio.sleep(2)

            await event.respond(f"✅ **Mission Successful!**\nApproved `{total_approved}` members in this chat.")
            
        except Exception as e:
            log.error(f"ApproveAll Error: {e}")
            await event.edit(f"❌ **Failed:** `{str(e)}` \n\nEnsure I am Admin with 'Add Members' rights.")

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
                    # 🔥 Dynamic Call for Auto-Approver
                    try:
                        hide_call = functions.messages.HideChatJoinRequestRequest(peer=update.peer, user_id=update.user_id, approved=True)
                    except AttributeError:
                        hide_call = CustomHideRequest(peer=update.peer, user_id=update.user_id, approved=True)
                    
                    await client(hide_call)
                    log.info(f"✅ Auto-approved {update.user_id}")
            except:
                pass
