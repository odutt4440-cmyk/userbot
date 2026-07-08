import asyncio
import logging
from telethon import events, types, functions
from telethon.errors import FloodWaitError, HideRequesterMissingError
from database import set_approve_settings, get_approve_settings

log = logging.getLogger(__name__)

def register(client):

    # --- 1. APPROVE ALL PENDING (.approveall) - AUTO-RETRY VERSION ✅ ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approveall'))
    async def approve_all_handler(event):
        if event.is_private:
            return await event.edit("❌ **Error:** Please run this command INSIDE the group.")

        msg = await event.edit("🔄 **Approving all pending join requests...**")
        chat_id = event.chat_id

        try:
            chat = await client.get_entity(chat_id)
            
            batch_count = 0
            total_approved = 0
            consecutive_fails = 0
            max_consecutive_fails = 3  # 3 baar fail hua to stop
            max_batches = 100  # Safety cap
            
            while consecutive_fails < max_consecutive_fails and batch_count < max_batches:
                try:
                    # Call HideAll - har baar ~200 requests approve hoti hain
                    await client(functions.messages.HideAllChatJoinRequestsRequest(
                        peer=chat,
                        approved=True
                    ))
                    
                    batch_count += 1
                    total_approved += 200  # Approx count
                    consecutive_fails = 0  # Reset fail counter on success
                    
                    await msg.edit(
                        f"✅ **Batch {batch_count} done**\n"
                        f"📊 Total approved: ~`{total_approved}`\n"
                        f"⏳ Next batch in 30 seconds..."
                    )
                    
                    # ⚡ IMPORTANT: 30 second delay between batches
                    # Yeh Telegram ko reset time dega
                    await asyncio.sleep(30)
                    
                except HideRequesterMissingError:
                    # ✅ Koi pending nahi bacha - done!
                    await msg.edit(
                        f"✅ **All done!**\n"
                        f"📊 Total batches: `{batch_count}`\n"
                        f"👥 Total approved: ~`{total_approved}`\n"
                        f"📭 No more pending requests."
                    )
                    return
                    
                except TimeoutError:
                    consecutive_fails += 1
                    log.warning(f"⏱️ Timeout #{consecutive_fails}, waiting 60s...")
                    await msg.edit(
                        f"⏱️ **Timeout #{consecutive_fails}**\n"
                        f"⏳ Waiting 60 seconds before retry..."
                    )
                    await asyncio.sleep(60)
                    continue
                    
                except FloodWaitError as f:
                    wait_time = f.seconds
                    log.warning(f"🌊 Flood wait: {wait_time}s")
                    await msg.edit(f"🌊 **Rate limited.** Sleeping `{wait_time}`s...")
                    await asyncio.sleep(wait_time)
                    consecutive_fails = 0  # FloodWait normal hai, fail count reset
                    continue
                    
                except Exception as api_err:
                    error_str = repr(api_err)
                    log.error(f"Batch error: {error_str}")
                    
                    # Check if it's "unsuccessful" error (Telethon internal)
                    if "unsuccessful" in error_str.lower() or "timeout" in error_str.lower():
                        consecutive_fails += 1
                        wait = 30 * consecutive_fails  # 30, 60, 90 sec
                        await msg.edit(
                            f"⚠️ **Error in batch {batch_count+1}**\n"
                            f"⏳ Waiting `{wait}`s before retry..."
                        )
                        await asyncio.sleep(wait)
                        continue
                    else:
                        # Unknown error - report it
                        return await msg.edit(f"❌ **Fatal Error:** `{error_str}`")
            
            # Loop ended - report summary
            if batch_count > 0:
                await msg.edit(
                    f"✅ **Process completed!**\n"
                    f"📊 Total batches: `{batch_count}`\n"
                    f"👥 Total approved: ~`{total_approved}`\n\n"
                    f"💡 Agar aur pending hain to 2 minute baad `.approveall` phir se chalao."
                )
            else:
                await msg.edit("❌ **Could not process any batches.** Telegram might be limiting.")
            
        except Exception as e:
            error_details = repr(e)
            log.error(f"ApproveAll Fatal Error: {error_details}")
            await event.edit(f"❌ **Fatal Error:** `{error_details}`")

    # --- 2. APPROVE BY ID ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.approve (\d+)'))
    async def approve_by_id_handler(event):
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
        
        if "PendingJoinRequests" in update_name or "ChatInviteRequester" in update_name:
            try:
                me = await client.get_me()
                if await get_approve_settings(me.id):
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
                    
                    elif hasattr(update, 'peer') and update.peer:
                        await client(functions.messages.HideAllChatJoinRequestsRequest(
                            peer=update.peer,
                            approved=True
                        ))
                        log.info(f"✅ Auto-approved all pending for chat: {update.peer}")
                        
            except Exception as e:
                log.error(f"Auto-approve error: {repr(e)}")
