import asyncio
import re
import logging
from telethon import events, functions, types
from database import set_reaction_data, get_reaction_data, db # Database se db object zaroori hai

log = logging.getLogger(__name__)

# --- GLOBAL MEMORY (Taaki restart par bhi cache rahe) ---
REACT_TARGETS = {} # {user_id: {chat_id: emoji}}
REACT_ALL = {}     # {user_id: {chat_id: emoji}}

def register(client):
    
    # 🔥 SYNC LOGIC: Jab module load ho, database se settings uthao
    async def sync_reactions():
        me = await client.get_me()
        user_id = me.id
        
        # Database se is user ki saari reaction settings nikalo
        cursor = db["reaction_settings"].find({"user_id": user_id})
        async for doc in cursor:
            c_id = doc["chat_id"]
            emoji = doc["emoji"]
            active = doc.get("active", 1)
            
            if not active: continue
            
            if c_id == "global": # Agar future me global reaction lagana ho
                pass 
            else:
                # Fill Memory Cache
                if user_id not in REACT_ALL: REACT_ALL[user_id] = {}
                REACT_ALL[user_id][c_id] = emoji
        log.info(f"🎭 Reactions Synced from DB for {user_id}")

    # Start Sync Task
    client.loop.create_task(sync_reactions())

    # --- 1. ENABLE AUTO-REACT COMMAND ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.autoreact(?:\s+(.*))?'))
    async def enable_react(event):
        emoji = event.pattern_match.group(1)
        if not emoji:
            return await event.edit("❌ **Error:** Provide an emoji. Example: `.autoreact 🔥` ")

        chat_id = event.chat_id
        me = await client.get_me()
        user_id = me.id
        
        if user_id not in REACT_ALL: REACT_ALL[user_id] = {}
        
        if event.is_reply:
            # --- TARGET SPECIFIC USER ---
            reply = await event.get_reply_message()
            target_id = reply.sender_id
            
            if user_id not in REACT_TARGETS: REACT_TARGETS[user_id] = {}
            if chat_id not in REACT_TARGETS[user_id]: REACT_TARGETS[user_id][chat_id] = {}
            
            REACT_TARGETS[user_id][chat_id][target_id] = emoji
            await event.edit(f"🎭 **Target Set:** Reacting with {emoji} to this user.")
        else:
            # --- TARGET EVERYONE IN CHAT ---
            REACT_ALL[user_id][chat_id] = emoji
            await event.edit(f"🎭 **GC Mode:** Reacting with {emoji} to **ALL** messages here.")

        # Save to DB for permanent persistence
        await set_reaction_data(user_id, chat_id, emoji)
        await asyncio.sleep(3)
        await event.delete()

    # --- 2. STOP AUTO-REACT ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.stopreact'))
    async def stop_react(event):
        chat_id = event.chat_id
        me = await client.get_me()
        user_id = me.id
        
        count = 0
        if user_id in REACT_ALL and chat_id in REACT_ALL[user_id]:
            del REACT_ALL[user_id][chat_id]
            count += 1
        if user_id in REACT_TARGETS and chat_id in REACT_TARGETS[user_id]:
            del REACT_TARGETS[user_id][chat_id]
            count += 1
            
        # DB me status update (Active=0)
        await db["reaction_settings"].update_one(
            {"user_id": user_id, "chat_id": chat_id},
            {"$set": {"active": 0}}
        )
        
        if count > 0:
            await event.edit("🛑 **Auto-Reaction Disabled.**")
        else:
            await event.edit("⚠️ No active reactions to stop.")
        await asyncio.sleep(2)
        await event.delete()

    # --- 3. THE REACTION ENGINE ---
    @client.on(events.NewMessage(incoming=True))
    async def reaction_worker(event):
        chat_id = event.chat_id
        sender_id = event.sender_id
        me = await client.get_me()
        user_id = me.id
        
        emoji = None

        # 1. Check if 'React to All' is in memory for this user/chat
        if user_id in REACT_ALL and chat_id in REACT_ALL[user_id]:
            emoji = REACT_ALL[user_id][chat_id]
        
        # 2. Check if specific user is targeted in this chat
        elif (user_id in REACT_TARGETS and 
              chat_id in REACT_TARGETS[user_id] and 
              sender_id in REACT_TARGETS[user_id][chat_id]):
            emoji = REACT_TARGETS[user_id][chat_id][sender_id]

        if emoji:
            # Don't react to yourself or other bots
            if event.out: return
            sender = await event.get_sender()
            if sender and getattr(sender, 'bot', False): return

            try:
                # 🔥 Send Reaction
                await client(functions.messages.SendReactionRequest(
                    peer=event.input_chat,
                    msg_id=event.id,
                    add_to_recent=True,
                    reaction=[types.ReactionEmoji(emoticon=emoji)]
                ))
            except Exception as e:
                # Agar Telegram ne block kiya ya emoji valid nahi hai
                log.debug(f"Reaction fail: {e}")
