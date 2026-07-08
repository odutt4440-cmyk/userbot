import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError, HideRequesterMissingError, RPCError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # --- 1. APPROVE ALL PENDING (.approveall) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        msg = await event.edit("🔄 **Approving join requests in batches...**")
        chat_id = event.chat_id

        try:
            chat = await client.get_entity(chat_id)
            total_approved = 0
            failed_batches = 0
            max_failures = 3  # Stop after this many consecutive failures
            
            await msg.edit(f"⏳ **Working...** (Batches: 0, Approved: 0)")
            
            # We'll call HideAll repeatedly in a loop.
            # Each call approves a BATCH of pending requests (Telegram's internal batch size).
            # When no more are pending, it raises HideRequesterMissingError - that's our stop signal.
            for batch_num in range(1, 51):  # Max 50 batches (safety limit)
                try:
                    await client(functions.messages.HideAllChatJoinRequestsRequest(
                        peer=chat,
                        approved=True
                    ))
                    
                    total_approved += 1  # We count batches, exact count is hard without the fetch method
                    failed_batches = 0
                    
                    await msg.edit(f"⏳ **Working...** (Batch: `{batch_num}`, ~`{total_approved * 50}`+ approved)")
                    
                    # ⏱️ CRITICAL: Wait between batches to avoid rate limits
                    await asyncio.sleep(2 + (batch_num // 10))  # Gradually increase delay
                    
                except HideRequesterMissingError:
                    # ✅ No more pending requests - we're done
                    log.info(f"No more pending requests after batch {batch_num}")
                    break
                    
                except FloodWaitError as f:
                    log.warning(f"Flood wait: {f.seconds}s")
                    await msg.edit(f"⚠️ **Rate limited.** Sleeping `{f.seconds}`s...")
                    await asyncio.sleep(f.seconds)
                    failed_batches = 0  # Don't break on flood wait
                    continue
                    
                except RPCError as rpc_err:
                    error_str = str(rpc_err)
                    # If Telegram says "no requests", we're done
                    if "HIDE_REQUESTER_MISSING" in error_str or "no requests" in error_str.lower():
                        break
                    
                    failed_batches += 1
                    log.warning(f"Batch {batch_num} failed: {error_str}")
                    
                    if failed_batches >= max_failures:
                        log.error(f"Stopping after {max_failures} consecutive failures")
                        break
                    
                    await asyncio.sleep(3)
                    continue
                    
                except TimeoutError:
                    # Timeout = probably still processing OR overloaded
                    failed_batches += 1
                    log.warning(f"Batch {batch_num} timed out")
                    
                    if failed_batches >= max_failures:
                        break
                    
                    # Wait longer after timeout
                    await asyncio.sleep(5)
                    continue
            
            # Final report
            if total_approved == 0:
                await msg.edit("📭 **No pending join requests found.**")
            else:
                await msg.edit(
                    f"✅ **Done!**\n"
                    f"• Total batches: `{total_approved}`\n"
                    f"• Estimated approved: `~{total_approved * 50}`+\n"
                    f"• Tip: Use `.checkpending` to verify if any remain."
                )
            
        except Exception as e:
            error_details = repr(e)
            log.error(f"ApproveAll Fatal Error: {error_details}")
            await event.edit(f"❌ **Fatal Error:** `{error_details}`")

    # --- 2. CHECK PENDING REQUESTS (.checkpending) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.checkpending'))
    async def check_pending_handler(event):
        """Check if any pending join requests exist by attempting a small hide operation."""
        if event.is_private:
            return await event.edit("❌ Please run this in a group.")
        
        chat = await client.get_entity(event.chat_id)
        
        try:
            # Try to approve a single batch - if HideRequesterMissingError, none pending
            result = await client(functions.messages.HideAllChatJoinRequestsRequest(
                peer=chat,
                approved=True
            ))
            
            # If it succeeded, there ARE pending requests
            # But we just approved them, so tell the user
            await event.edit("✅ **Pending requests existed and were approved!**")
            
        except HideRequesterMissingError:
            await event.edit("📭 **No pending join requests.** All clear!")
        except Exception as e:
            await event.edit(f"❌ **Error checking:** `{repr(e)}`")

    # --- 3. APPROVE BY USER ID (.approve <id>) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approve (\d+)'))
    async def approve_by_id_handler(event):
        if event.is_private:
            return await event.edit("❌ Please run this INSIDE the group.")
        
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
            await event.edit(f"⚠️ **No pending request found for user:** `{user_id}`")
        except Exception as e:
            await event.edit(f"❌ **Error:** `{repr(e)}`")

    # --- 4. TOGGLE AUTO-APPROVE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.autoapprove (on|off)'))
    async def toggle_auto(event):
        mode = event.pattern_match.group(1).lower()
        is_on = (mode == "on")
        await set_approve_settings(event.sender_id, is_on)
        status = "ENABLED ✅" if is_on else "DISABLED 🛑"
        await event.edit(f"🛡️ **Join Guard:** Auto-approve is now **{status}**.")

    # --- 5. RAW HANDLER FOR NEW REQUESTS (AUTO-APPROVE) ---
    @client.on(events.Raw())
    async def raw_handler(update):
        update_name = type(update).__name__
        
        # UpdateBotChatInviteRequester = new join request (bot accounts)
        # UpdatePendingJoinRequests = pending count changed
        if "BotChatInviteRequester" in update_name or "PendingJoinRequests" in update_name:
            try:
                me = await client.get_me()
                settings = await get_approve_settings(me.id)
                if not settings:
                    return
                
                # If settings is True or dict with enabled=True
                auto_enabled = settings if isinstance(settings, bool) else settings.get('enabled', False)
                if not auto_enabled:
                    return
                
                # For BotChatInviteRequester, we have the exact user_id
                if hasattr(update, 'user_id') and update.user_id and hasattr(update, 'peer'):
                    try:
                        user_id = update.user_id
                        user = await client.get_entity(user_id) if isinstance(user_id, int) else user_id
                        
                        await client(functions.messages.HideChatJoinRequestRequest(
                            peer=update.peer,
                            user_id=user,
                            approved=True
                        ))
                        log.info(f"✅ Auto-approved user: {user_id}")
                    except HideRequesterMissingError:
                        pass  # Already handled
                    except Exception as e:
                        log.error(f"Auto-approve single error: {repr(e)}")
                
                # For PendingJoinRequests updates, do a quick HideAll
                elif "PendingJoinRequests" in update_name and hasattr(update, 'peer'):
                    try:
                        await client(functions.messages.HideAllChatJoinRequestsRequest(
                            peer=update.peer,
                            approved=True
                        ))
                        log.info(f"✅ Auto-approved pending batch")
                    except HideRequesterMissingError:
                        pass
                    except Exception as e:
                        log.error(f"Auto-approve batch error: {repr(e)}")
                        
            except Exception as e:
                log.error(f"Raw handler error: {repr(e)}")
