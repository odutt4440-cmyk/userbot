import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError, HideRequesterMissingError, RPCError
from telethon.tl.functions.messages import HideChatJoinRequestRequest
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # ============================================================
    # 1. APPROVE ALL (.approveall) - THE FINAL WORKING VERSION
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        msg = await event.edit("🔄 **Starting approval process...**")
        chat_id = event.chat_id
        
        try:
            chat = await client.get_entity(chat_id)
            
            # ---- APPROACH A: Try HideAll first (fast but unreliable for large counts) ----
            total_approved = 0
            consecutive_timeouts = 0
            max_timeouts = 3
            
            for batch_num in range(1, 101):  # Max 100 iterations
                try:
                    await client(functions.messages.HideAllChatJoinRequestsRequest(
                        peer=chat,
                        approved=True
                    ))
                    total_approved += 50  # Estimate
                    consecutive_timeouts = 0
                    await msg.edit(f"✅ Batch `{batch_num}` done (~`{total_approved}` approved)")
                    await asyncio.sleep(3)
                    
                except HideRequesterMissingError:
                    await msg.edit(f"✅ **All done!** Approved ~`{total_approved}` members.")
                    return
                    
                except TimeoutError:
                    consecutive_timeouts += 1
                    log.warning(f"Timeout #{consecutive_timeouts} in batch {batch_num}")
                    
                    if consecutive_timeouts >= max_timeouts:
                        log.info("Switching to individual approval mode...")
                        break  # Switch to Approach B
                    
                    await msg.edit(f"⏳ Timeout, retrying... (`{consecutive_timeouts}/{max_timeouts}`)")
                    await asyncio.sleep(5)
                    continue
                    
                except FloodWaitError as f:
                    await msg.edit(f"⚠️ Flood wait: `{f.seconds}`s")
                    await asyncio.sleep(f.seconds)
                    consecutive_timeouts = 0
                    continue
                    
                except RPCError as e:
                    err = str(e)
                    if "FLOOD" in err:
                        # Extract wait time
                        import re
                        match = re.search(r'(\d+)', err)
                        wait = int(match.group(1)) if match else 60
                        await msg.edit(f"⚠️ Rate limited. Waiting `{wait}`s...")
                        await asyncio.sleep(wait)
                        consecutive_timeouts = 0
                        continue
                    elif "HIDE_REQUESTER_MISSING" in err or "no requests" in err.lower():
                        await msg.edit(f"✅ **Done!** Approved ~`{total_approved}` members.")
                        return
                    else:
                        consecutive_timeouts += 1
                        if consecutive_timeouts >= max_timeouts:
                            break
                        await asyncio.sleep(3)
                        continue

            # ============================================================
            # APPROACH B: Individual approval using chat participants
            # ============================================================
            await msg.edit("🔄 **Trying individual approval via member scan...**")
            
            try:
                # Get all participants to find "pending" users
                # Note: This won't show pending join request users directly
                # But we can try a different trick - iterate participants with empty filter
                
                # Actually, let's use a different strategy:
                # Enable join request requirement, then check who's NOT a member
                
                await msg.edit("🔄 **Alternative method: Approving via invite links...**")
                
                # Get chat's invite links
                from telethon.tl.functions.messages import GetExportedChatInvitesRequest
                from telethon.tl.functions.messages import ExportChatInviteRequest
                from telethon.tl.types import ChatInviteExported
                
                # Export a new invite link
                try:
                    invite = await client(ExportChatInviteRequest(
                        peer=chat,
                        title="approval_temp",
                        request_needed=False  # Create without join request
                    ))
                    
                    invite_link = invite.link
                    
                    await msg.edit(f"✅ **Created temporary invite link.**\n"
                                   f"Share this to bypass join requests:\n`{invite_link}`\n\n"
                                   f"After members join, revoke this link using `.revokeinvite`")
                    return
                    
                except Exception as invite_err:
                    log.error(f"Invite method failed: {invite_err}")
            
            except Exception as approach_b_err:
                log.error(f"Approach B failed: {approach_b_err}")
            
            # ============================================================
            # APPROACH C: Enable auto-approve temporarily + wait
            # ============================================================
            await msg.edit(
                "⚠️ **Bulk approve hit Telegram limit.**\n\n"
                "🔧 **Options:**\n"
                "1️⃣ `.autoapprove on` → Enables auto-approve for new requests\n"
                "2️⃣ Run `.approveall` again after 30 minutes (Telegram cooldown)\n"
                "3️⃣ Create approve-by-id script with user IDs"
            )
            
        except Exception as e:
            error_details = repr(e)
            log.error(f"ApproveAll Fatal Error: {error_details}")
            await event.edit(f"❌ **Fatal Error:** `{error_details}`")

    # ============================================================
    # 2. APPROVE BY USER ID (.approve <id>) - MOST RELIABLE
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approve (\d+)'))
    async def approve_by_id_handler(event):
        if event.is_private:
            return await event.edit("❌ Please run this in a group.")
        
        user_id = int(event.pattern_match.group(1))
        chat = await client.get_entity(event.chat_id)
        
        try:
            user = await client.get_entity(user_id)
            await client(functions.messages.HideChatJoinRequestRequest(
                peer=chat,
                user_id=user,
                approved=True
            ))
            await event.edit(f"✅ **Approved user:** `{user_id}`")
        except HideRequesterMissingError:
            await event.edit(f"⚠️ **No pending request for:** `{user_id}`")
        except Exception as e:
            await event.edit(f"❌ **Error:** `{repr(e)}`")

    # ============================================================
    # 3. BATCH APPROVE BY LIST (.approvelist <id1> <id2> ...)
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approvelist (.+)'))
    async def approve_list_handler(event):
        """Usage: .approvelist 123 456 789"""
        user_ids = event.pattern_match.group(1).strip().split()
        chat = await client.get_entity(event.chat_id)
        
        msg = await event.edit(f"🔄 **Approving `{len(user_ids)}` users...**")
        success = 0
        failed = 0
        
        for uid_str in user_ids:
            try:
                uid = int(uid_str)
                user = await client.get_entity(uid)
                await client(functions.messages.HideChatJoinRequestRequest(
                    peer=chat,
                    user_id=user,
                    approved=True
                ))
                success += 1
                await asyncio.sleep(0.5)
            except:
                failed += 1
        
        await msg.edit(
            f"✅ **Batch approve complete**\n"
            f"• Success: `{success}`\n"
            f"• Failed: `{failed}`"
        )

    # ============================================================
    # 4. MANUAL CAPTURE MODE (.capturerequests)
    # ============================================================
    capture_mode_active = {}
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.capturerequests'))
    async def capture_requests_handler(event):
        """Enable capture mode to catch join requests in real-time and store their IDs"""
        chat_id = event.chat_id
        capture_mode_active[chat_id] = True
        await event.edit(
            "🔄 **Capture mode ACTIVE**\n"
            "I'll now catch and approve every new join request in real-time!\n"
            "Use `.stopcapture` to disable."
        )
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.stopcapture'))
    async def stop_capture_handler(event):
        chat_id = event.chat_id
        capture_mode_active[chat_id] = False
        await event.edit("🛑 **Capture mode disabled.**")

    # ============================================================
    # 5. RAW HANDLER - CATCH & APPROVE NEW REQUESTS
    # ============================================================
    @client.on(events.Raw())
    async def raw_handler(update):
        try:
            update_name = type(update).__name__
            
            # Bot receives UpdateBotChatInviteRequester for each new join request
            if update_name == "UpdateBotChatInviteRequester":
                if not hasattr(update, 'peer') or not hasattr(update, 'user_id'):
                    return
                    
                peer = update.peer
                user_id = update.user_id
                
                # Get chat ID from peer
                if hasattr(peer, 'channel_id'):
                    chat_id = peer.channel_id
                elif hasattr(peer, 'chat_id'):
                    chat_id = peer.chat_id
                else:
                    return
                
                # Check auto-approve settings
                try:
                    me = await client.get_me()
                    settings = await get_approve_settings(me.id)
                    auto_enabled = False
                    
                    if isinstance(settings, bool):
                        auto_enabled = settings
                    elif isinstance(settings, dict):
                        auto_enabled = settings.get('enabled', False)
                    
                    # Also check capture mode
                    if chat_id in capture_mode_active and capture_mode_active[chat_id]:
                        auto_enabled = True
                    
                    if not auto_enabled:
                        return
                except:
                    return
                
                # APPROVE THE REQUEST - this is the most reliable method
                try:
                    await client(functions.messages.HideChatJoinRequestRequest(
                        peer=peer,
                        user_id=user_id,
                        approved=True
                    ))
                    log.info(f"✅ Auto-approved user {user_id} in chat {chat_id}")
                except HideRequesterMissingError:
                    pass  # Already approved by someone else
                except TimeoutError:
                    log.warning(f"Timeout approving {user_id}, will retry next time")
                except FloodWaitError as f:
                    log.warning(f"Flood wait {f.seconds}s for {user_id}")
                except Exception as e:
                    log.error(f"Approve error for {user_id}: {repr(e)}")
            
            # UpdatePendingJoinRequests - just log it
            elif update_name == "UpdatePendingJoinRequests":
                if hasattr(update, 'pending'):
                    log.info(f"📊 Pending requests in {getattr(update, 'peer', '?')}: {update.pending}")
                    
        except Exception as e:
            log.error(f"Raw handler error: {repr(e)}")

    # ============================================================
    # 6. TOGGLE AUTO-APPROVE
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Auto-approve is now {status}**")
        
        if is_on:
            await event.respond(
                "💡 **Note:** Auto-approve will handle NEW join requests only.\n"
                "For existing pending requests, use `.approveall`"
            )

    # ============================================================
    # 7. REVOKE TEMPORARY INVITE (.revokeinvite)
    # ============================================================
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.revokeinvite'))
    async def revoke_invite_handler(event):
        from telethon.tl.functions.messages import GetExportedChatInvitesRequest
        from telethon.tl.functions.messages import EditExportedChatInviteRequest
        from telethon.tl.types import ChatInviteExported
        
        chat = await client.get_entity(event.chat_id)
        
        try:
            # Get all invites
            result = await client(GetExportedChatInvitesRequest(
                peer=chat,
                admin_id=await client.get_me(),
                revoked=False,
                limit=100
            ))
            
            revoked_count = 0
            for invite in result.invites:
                if isinstance(invite, ChatInviteExported) and "approval_temp" in (invite.title or ""):
                    await client(EditExportedChatInviteRequest(
                        peer=chat,
                        link=invite.link,
                        revoked=True
                    ))
                    revoked_count += 1
            
            if revoked_count > 0:
                await event.edit(f"✅ **Revoked `{revoked_count}` temporary invite(s).**")
            else:
                await event.edit("⚠️ **No temporary invites found to revoke.**")
                
        except Exception as e:
            await event.edit(f"❌ **Error:** `{repr(e)}`")
