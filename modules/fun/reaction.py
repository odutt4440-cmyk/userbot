import asyncio
import re
import logging
from telethon import events, functions, types
from database import set_reaction_data, get_reaction_data, db

log = logging.getLogger(__name__)

# --- GLOBAL MEMORY (Multi-user safe) ---
# Format: {owner_id: {chat_id: emoji}}
REACT_ALL = {}
# Format: {owner_id: {chat_id: {target_user_id: emoji}}}
REACT_TARGETS = {}

def register(client):
    
    async def sync_reactions():
        try:
            me = await client.get_me()
            user_id = me.id
            
            cursor = db["reaction_settings"].find({"user_id": user_id, "active": 1})
            async for doc in cursor:
                c_id = doc["chat_id"]
                emoji = doc["emoji"]
                
                # Check if it was a target-specific or chat-wide setting
                # (Assuming database structure stores target info if needed)
                if user_id not in REACT_ALL: REACT_ALL[user_id] = {}
                REACT_ALL[user_id][c_id] = emoji
                
            log.info(f"🎭 Reactions Synced for {user_id}")
        except Exception as e:
            log.error(f"Sync Error: {e}")

    # Start Sync
    client.loop.create_task(sync_reactions())

    # --- 1. ENABLE AUTO-REACT ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.autoreact(?:\s+(.*))?'))
    async def enable_react(event):
        emoji = event.pattern_match.group(1)
        if not emoji:
            return await event.edit("❌ **Error:** Provide an emoji. Example: `.autoreact 🔥` ")

        chat_id = event.chat_id
        me = await client.get_me()
        user_id = me.id
        
        if user_id not in REACT_ALL: REACT_ALL[user_id] = {}
        if user_id not in REACT_TARGETS: REACT_TARGETS[user_id] = {}

        if event.is_reply:
            # --- TARGET SPECIFIC USER (Can be a Bot!) ---
            reply = await event.get_reply_message()
            target_id = reply.sender_id
            
            if chat_id not in REACT_TARGETS[user_id]: REACT_TARGETS[user_id][chat_id] = {}
            REACT_TARGETS[user_id][chat_id][target_id] = emoji
            
            # Remove from 'All' if they were there
            if chat_id in REACT_ALL[user_id]: del REACT_ALL[user_id][chat_id]
            
            await event.edit(f"🎭 **Target Set:** Reacting with {emoji} to this specific user/bot.")
        else:
            # --- TARGET EVERYONE IN CHAT ---
            REACT_ALL[user_id][chat_id] = emoji
            await event.edit(f"🎭 **GC Mode:** Reacting with {emoji} to **ALL** messages here.")

        await set_reaction_data(user_id, chat_id, emoji)
        await asyncio.sleep(3)
        await event.delete()

    # --- 2. STOP AUTO-REACT ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.stopreact'))
    async def stop_react(event):
        chat_id = event.chat_id
        me = await client.get_me()
        user_id = me.id
        
        if user_id in REACT_ALL and chat_id in REACT_ALL[user_id]:
            del REACT_ALL[user_id][chat_id]
        if user_id in REACT_TARGETS and chat_id in REACT_TARGETS[user_id]:
            del REACT_TARGETS[user_id][chat_id]
            
        await db["reaction_settings"].update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$set": {"active": 0}}
        )
        await event.edit("🛑 **Auto-Reaction Disabled.**")
        await asyncio.sleep(2)
        await event.delete()

    # --- 3. THE REACTION ENGINE ---
    @client.on(events.NewMessage(incoming=True))
    async def reaction_worker(event):
        # Only process if we have an active owner
        me = await client.get_me()
        user_id = me.id
        
        chat_id = event.chat_id
        sender_id = event.sender_id
        emoji = None

        # 1. Check Specific Target First
        if (user_id in REACT_TARGETS and 
            chat_id in REACT_TARGETS[user_id] and 
            sender_id in REACT_TARGETS[user_id][chat_id]):
            emoji = REACT_TARGETS[user_id][chat_id][sender_id]
        
        # 2. Check Global Chat Setting
        elif user_id in REACT_ALL and chat_id in REACT_ALL[user_id]:
            emoji = REACT_ALL[user_id][chat_id]

        if emoji:
            # 🔥 FIX: Apne khud ke messages par react mat karo
            if event.out: return
            
            # 🔥 FIX: Doosre bots par react karne ki permission di (Removed bot check)
            
            try:
                await client(functions.messages.SendReactionRequest(
                    peer=event.input_chat,
                    msg_id=event.id,
                    add_to_recent=True,
                    reaction=[types.ReactionEmoji(emoticon=emoji)]
                ))
            except Exception as e:
                log.debug(f"Reaction fail: {e}")
