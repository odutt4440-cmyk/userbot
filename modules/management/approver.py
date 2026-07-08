import asyncio
import logging
import re
from telethon import events, types, functions
from telethon.errors import FloodWaitError, HideRequesterMissingError
from telethon.tl.functions.messages import HideChatJoinRequestRequest
from telethon.tl.types import (
    TypeInputPeer, InputPeerChannel, InputPeerChat
)
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # ============================================================
    # 1. APPROVE ALL - ID-BASED BATCH APPROVAL
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        msg = await event.edit("🔄 **Starting batch approval...**")
        chat_id = event.chat_id

        try:
            chat = await client.get_entity(chat_id)
            
            # STEP 1: Get admin log to find recent join request user IDs
            await msg.edit("🔄 **Scanning recent join requests from admin log...**")
            
            from telethon.tl.functions.channels import GetAdminLogRequest
            from telethon.tl.types import InputChannel, ChannelAdminLogEventsFilter
            
            # Get chat as InputChannel
            input_channel = None
            if hasattr(chat, 'id'):
                access_hash = getattr(chat, 'access_hash', 0)
                input_channel = InputChannel(chat.id, access_hash)
            
            if not input_channel:
                # Try getting via entity
                return await msg.edit("❌ **Couldn't get channel input. Try in a supergroup/channel.**")
            
            # Fetch recent admin log entries to find join requests
            # Admin log mein "join requests" ka koi direct filter nahi, 
            # lekin hum participants change events dekh sakte hain
            
            pending_ids = []
            
            # TRY METHOD 1: Get participants with "request" filter (Telethon 1.44 specific)
            try:
                from telethon.tl.types import ChannelParticipantsSearch
                
                # Supergroup/channel participants search with empty query to get all members
                # Pending request users WON'T appear here, but we can try the admins list
                from telethon.tl.functions.channels import GetParticipantsRequest
                from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantsBots
                
                # This won't show pending users directly, skip
                pass
            except:
                pass
            
            # METHOD 2: Try brute-force with a range of sequential user IDs
            # Telegram groups mein recent join requests usually recent IDs hoti hain
            # But this is impractical for 1397 users
            
            # ✅ FINAL METHOD: Let's create a temporary bot API bridge
            # Actually, we'll use a smart approach: 
            # Fetch recent messages to find "joined via invite" system messages
            
            await msg.edit("🔄 **Method: Sequential approve via smart ID collection...**")
            
            # Get chat's recent join dates via participants
            # Everyone who is ALREADY a member is not pending
            # So we need pending IDs. Here's what works:
            
            # Check if we can use the GetChatJoinRequests TL method 
            # by importing it from a newer layer
            try:
                # Direct layer method - some Telethon 1.44 builds have it
                from telethon.tl.functions.messages import GetChatJoinRequestsRequest as GetReq
                has_get_requests = True
            except ImportError:
                has_get_requests = False
            
            if has_get_requests:
                try:
                    await msg.edit("🔄 **Fetching pending requests (layer method found)...**")
                    offset = None
                    all_requests = []
                    
                    while True:
                        try:
                            if offset:
                                result = await client(GetReq(
                                    peer=chat,
                                    limit=100,
                                    offset_date=offset.date if hasattr(offset, 'date') else None,
                                    offset_user=offset.user_id if hasattr(offset, 'user_id') else None
                                ))
                            else:
                                result = await client(GetReq(
                                    peer=chat,
                                    limit=100
                                ))
                        except Exception as e:
                            if "not found" in str(e).lower():
                                break
                            raise
                        
                        if not result or not hasattr(result, 'requests') or not result.requests:
                            break
                        
                        for req in result.requests:
                            user_id = getattr(req, 'user_id', None)
                            if user_id:
                                all_requests.append(user_id)
                        
                        if len(result.requests) < 100:
                            break
                        
                        offset = result.requests[-1]
                        await asyncio.sleep(0.5)
                    
                    pending_ids = all_requests
                    
                except Exception as e:
                    log.warning(f"Layer method failed: {e}")
                    pending_ids = []
            
            # If layer method didn't work or returned nothing
            if not pending_ids:
                # METHOD 3: Let user provide IDs via text file/scraping
                # But for now, show error with instructions
                return await msg.edit(
                    "❌ **Cannot fetch pending IDs automatically in Telethon 1.44.**\n\n"
                    "🔧 **Solution:** I'll approve them ONE BY ONE using admin log IDs.\n"
                    "Use this alternative command:\n\n"
                    "```\n"
                    ".scanapprove\n"
                    "```\n"
                    "This will scan admin log and approve recent joiners."
                )
            
            # If we got IDs, process them
            total = len(pending_ids)
            await msg.edit(f"🔄 **Found `{total}` pending requests. Approving...**")
            
            success = 0
            failed = 0
            
            for i, uid in enumerate(pending_ids, 1):
                try:
                    user = await client.get_entity(uid)
                    await client(HideChatJoinRequestRequest(
                        peer=chat,
                        user_id=user,
                        approved=True
                    ))
                    success += 1
                    
                    if i % 10 == 0:
                        await msg.edit(f"⏳ **Progress:** `{i}/{total}` (✅{success} ❌{failed})")
                    
                    await asyncio.sleep(0.3)  # Rate limit safe
                    
                except HideRequesterMissingError:
                    success += 1  # Already approved
                    await asyncio.sleep(0.1)
                except FloodWaitError as f:
                    await msg.edit(f"⚠️ **Rate limited.** Sleeping `{f.seconds}`s...")
                    await asyncio.sleep(f.seconds)
                except Exception:
                    failed += 1
                    await asyncio.sleep(0.2)
            
            await msg.edit(
                f"✅ **Approval complete!**\n"
                f"• Total: `{total}`\n"
                f"• Approved: `{success}`\n"
                f"• Failed: `{failed}`"
            )
            
        except Exception as e:
            await msg.edit(f"❌ **Fatal Error:** `{repr(e)}`")

    # ============================================================
    # 2. SCAN & APPROVE FROM ADMIN LOG (.scanapprove)
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.scanapprove'))
    async def scan_approve_handler(event):
        """Scan admin log and approve any pending join requests found"""
        if event.is_private:
            return await event.edit("❌ Please run this in a group.")
        
        msg = await event.edit("🔄 **Scanning admin log for join requests...**")
        chat = await client.get_entity(event.chat_id)
        
        try:
            from telethon.tl.functions.channels import GetAdminLogRequest
            from telethon.tl.types import InputChannel
            
            # Get InputChannel
            access_hash = getattr(chat, 'access_hash', 0)
            input_channel = InputChannel(chat.id, access_hash)
            
            # Fetch admin log (recent events)
            # We look for "joined" events
            result = await client(GetAdminLogRequest(
                channel=input_channel,
                q='',
                max_id=0,
                min_id=0,
                limit=100,
                events_filter=None,
                admins=None
            ))
            
            joined_users = []
            for entry in result.events:
                # Check if it's a join event
                action = getattr(entry, 'action', None)
                if action and 'join' in type(action).__name__.lower():
                    user = getattr(entry, 'user_id', None)
                    if user:
                        joined_users.append(user)
            
            if not joined_users:
                return await msg.edit("📭 **No recent join activity found in admin log.**")
            
            # Now try to approve each
            await msg.edit(f"🔄 **Found `{len(joined_users)}` recent joins. Checking for pending requests...**")
            
            approved = 0
            for uid in joined_users[:50]:  # Max 50 to avoid rate limits
                try:
                    await client(HideChatJoinRequestRequest(
                        peer=chat,
                        user_id=uid,
                        approved=True
                    ))
                    approved += 1
                    await asyncio.sleep(0.5)
                except HideRequesterMissingError:
                    # Already approved or not pending
                    pass
                except FloodWaitError as f:
                    await asyncio.sleep(f.seconds)
                except:
                    pass
            
            if approved > 0:
                await msg.edit(f"✅ **Approved `{approved}` from admin log.**\nRun again for more.")
            else:
                await msg.edit("📭 **No pending requests found in recent admin log.**")
            
        except Exception as e:
            await msg.edit(f"❌ **Error:** `{repr(e)}`")

    # ============================================================
    # 3. BATCH APPROVE FROM LIST (.approvelist)
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approvelist (.+)'))
    async def approve_list_handler(event):
        """Usage: .approvelist 123 456 789 (space-separated IDs)"""
        ids_str = event.pattern_match.group(1).strip()
        ids = re.findall(r'\d+', ids_str)
        
        if not ids:
            return await event.edit("❌ **No valid IDs found.** Usage: `.approvelist 123 456 789`")
        
        msg = await event.edit(f"🔄 **Approving `{len(ids)}` users...**")
        chat = await client.get_entity(event.chat_id)
        
        success, failed = 0, 0
        for i, uid_str in enumerate(ids, 1):
            try:
                uid = int(uid_str)
                user = await client.get_entity(uid)
                await client(HideChatJoinRequestRequest(
                    peer=chat,
                    user_id=user,
                    approved=True
                ))
                success += 1
                
                if i % 5 == 0:
                    await msg.edit(f"⏳ **Progress:** `{i}/{len(ids)}` (✅{success} ❌{failed})")
                
                await asyncio.sleep(0.5)
            except:
                failed += 1
                await asyncio.sleep(0.2)
        
        await msg.edit(f"✅ **Done!** Approved: `{success}`, Failed: `{failed}`")

    # ============================================================
    # 4. AUTO-APPROVE TOGGLE
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Auto-approve is now {status}**")

    # ============================================================
    # 5. RAW HANDLER - AUTO-APPROVE NEW REQUESTS
    # ============================================================
    @client.on(events.Raw())
    async def raw_handler(update):
        try:
            update_name = type(update).__name__
            
            if update_name == "UpdateBotChatInviteRequester":
                me = await client.get_me()
                settings = await get_approve_settings(me.id)
                
                auto_enabled = False
                if isinstance(settings, bool):
                    auto_enabled = settings
                elif isinstance(settings, dict):
                    auto_enabled = settings.get('enabled', False)
                
                if not auto_enabled or not hasattr(update, 'user_id'):
                    return
                
                try:
                    await client(HideChatJoinRequestRequest(
                        peer=update.peer,
                        user_id=update.user_id,
                        approved=True
                    ))
                    log.info(f"✅ Auto-approved user {update.user_id}")
                except:
                    pass
                    
        except Exception as e:
            log.error(f"Raw handler: {e}")
