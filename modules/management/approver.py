import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError, HideRequesterMissingError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # --- 1. APPROVE ALL PENDING (.approveall) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        await event.edit("🔄 **Approving all pending join requests...**")
        chat_id = event.chat_id

        try:
            chat = await client.get_entity(chat_id)
            
            # Method 1: Directly approve ALL pending requests in one go
            # Telethon 1.44 has HideAllChatJoinRequestsRequest
            try:
                result = await client(functions.messages.HideAllChatJoinRequestsRequest(
                    peer=chat,
                    approved=True
                ))
                
                # Count how many were approved from the updates
                count = 0
                if result:
                    for update in result.updates:
                        if hasattr(update, 'updates') and update.updates:
                            for u in update.updates:
                                if isinstance(u, types.UpdatePendingJoinRequests):
                                    count = getattr(u, 'pending', 0)
                                    break
                        elif isinstance(update, types.UpdatePendingJoinRequests):
                            count = getattr(update, 'pending', 0)
                            break
                
                await event.edit(f"✅ **Successfully approved all pending requests!**")
                
            except HideRequesterMissingError:
                await event.edit("📭 **No pending join requests found in this chat.**")
            except Exception as api_err:
                error_str = repr(api_err)
                log.error(f"HideAll failed: {error_str}")
                
                # Method 2: If HideAll fails, try fetching via get_participants approach
                # or just report the error
                if "FLOOD_WAIT" in error_str:
                    return await event.edit(f"⚠️ **Rate limited.** Try again later.")
                else:
                    return await event.edit(f"❌ **Error:** `{error_str}`")

        except Exception as e:
            error_details = repr(e)
            log.error(f"ApproveAll Fatal Error: {error_details}")
            await event.edit(f"❌ **Fatal Error:** `{error_details}`")

    # --- 2. APPROVE BY ID (new - exact method) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approve (\d+)'))
    async def approve_by_id_handler(event):
        """Usage: .approve 123456789 - Approve a specific user by ID"""
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        user_id = int(event.pattern_match.group(1))
        chat_id = event.chat_id

        try:
            chat = await client.get_entity(chat_id)
            user = await client.get_entity(user_id)
            
            await client(functions.messages.HideChatJoinRequestRequest(
                peer=chat,
                user_id=user,
                approved=True
            ))
            
            await event.edit(f"✅ **Approved user:** `{user_id}`")
        except Exception as e:
            await event.edit(f"❌ **Error:** `{repr(e)}`")

    # --- 3. TOGGLE AUTO-APPROVE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve is now **{status}**.")

    # --- 4. RAW HANDLER FOR NEW REQUESTS ---
    @client.on(events.Raw())
    async def raw_handler(update):
        update_name = type(update).__name__
        
        # Handle UpdatePendingJoinRequests and UpdateBotChatInviteRequester
        if "PendingJoinRequests" in update_name or "ChatInviteRequester" in update_name:
            try:
                me = await client.get_me()
                if await get_approve_settings(me.id):
                    # Extract IDs from the update
                    # UpdatePendingJoinRequests has: peer, pending, users (optional)
                    # UpdateBotChatInviteRequester has: peer, user_id, date, about, invite
                    
                    if hasattr(update, 'user_id') and update.user_id:
                        user_id = update.user_id
                        try:
                            user = await client.get_entity(user_id) if isinstance(user_id, int) else user_id
                        except:
                            user = user_id
                        
                        await client(functions.messages.HideChatJoinRequestRequest(
                            peer=update.peer,
                            user_id=user,
                            approved=True
                        ))
                        log.info(f"✅ Auto-approved user: {update.user_id}")
                    
                    # If there's no single user_id, try HideAll
                    elif hasattr(update, 'peer') and update.peer:
                        await client(functions.messages.HideAllChatJoinRequestsRequest(
                            peer=update.peer,
                            approved=True
                        ))
                        log.info(f"✅ Auto-approved all pending for chat: {update.peer}")
                        
            except Exception as e:
                log.error(f"Auto-approve error: {repr(e)}")
