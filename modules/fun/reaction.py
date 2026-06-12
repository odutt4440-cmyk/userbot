import asyncio
import re
from telethon import events, functions, types
from database import set_reaction_data, get_reaction_data

def register(client):
    # State Management
    # client.react_targets format: {chat_id: {user_id: emoji}}
    client.react_targets = {} 
    # client.react_all format: {chat_id: emoji}
    client.react_all = {}

    # --- 1. ENABLE AUTO-REACT COMMAND ---
    # Usage 1 (Target User): Reply to someone + `.autoreact 🔥`
    # Usage 2 (Whole Chat): Just type `.autoreact 🔥` in GC
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.autoreact(?:\s+(.*))?'))
    async def enable_react(event):
        emoji = event.pattern_match.group(1)
        if not emoji:
            return await event.edit("❌ **Error:** Provide an emoji. Example: `.autoreact 😂`")

        chat_id = event.chat_id
        
        if event.is_reply:
            # --- TARGET SPECIFIC USER ---
            reply = await event.get_reply_message()
            target_id = reply.sender_id
            
            if chat_id not in client.react_targets:
                client.react_targets[chat_id] = {}
            
            client.react_targets[chat_id][target_id] = emoji
            
            # Remove from 'react_all' if they were there
            if chat_id in client.react_all:
                del client.react_all[chat_id]

            user_target = await client.get_entity(target_id)
            name = user_target.first_name
            await event.edit(f"🎭 **Target Set:** Reacting to {emoji} on every message by **{name}**.")
        else:
            # --- TARGET EVERYONE IN GC ---
            client.react_all[chat_id] = emoji
            # Clear specific targets for this chat to avoid double reactions
            if chat_id in client.react_targets:
                del client.react_targets[chat_id]
                
            await event.edit(f"🎭 **GC Mode:** Reacting to {emoji} on **ALL** messages in this chat.")

        # Save setting to DB for persistence
        await set_reaction_data(event.sender_id, chat_id, emoji)
        await asyncio.sleep(4)
        await event.delete()

    # --- 2. STOP AUTO-REACT (.stopreact) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'(?i)^\.stopreact'))
    async def stop_react(event):
        chat_id = event.chat_id
        count = 0
        
        if chat_id in client.react_all:
            del client.react_all[chat_id]
            count += 1
        if chat_id in client.react_targets:
            del client.react_targets[chat_id]
            count += 1
            
        if count > 0:
            await event.edit("🛑 **Auto-Reaction Disabled** for this chat.")
        else:
            await event.edit("⚠️ No active reactions found here.")
            
        await asyncio.sleep(3)
        await event.delete()

    # --- 3. THE REACTION ENGINE (The Heart) ---
    @client.on(events.NewMessage(incoming=True))
    async def reaction_worker(event):
        chat_id = event.chat_id
        sender_id = event.sender_id
        emoji = None

        # Check if 'React to All' is enabled for this chat
        if chat_id in client.react_all:
            emoji = client.react_all[chat_id]
        
        # Check if this specific user is a target in this chat
        elif chat_id in client.react_targets and sender_id in client.react_targets[chat_id]:
            emoji = client.react_targets[chat_id][sender_id]

        if emoji:
            # Don't react to bots
            sender = await event.get_sender()
            if sender and getattr(sender, 'bot', False):
                return

            try:
                # Telegram SendReactionRequest
                await client(functions.messages.SendReactionRequest(
                    peer=event.chat_id,
                    msg_id=event.id,
                    add_to_recent=True,
                    reaction=[types.ReactionEmoji(emoticon=emoji)]
                ))
            except Exception as e:
                # Agar user ke paas premium emoji nahi hai ya chat me allowed nahi hai
                print(f"Reaction Error: {e}")
