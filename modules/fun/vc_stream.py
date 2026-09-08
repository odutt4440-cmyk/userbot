import asyncio
import os
from telethon import events
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from database import set_vc_chat, get_vc_chat

# Global store for VC instances
VC_SESSIONS = {} 

def register(client):

    async def get_call_handler(user_id):
        if user_id not in VC_SESSIONS:
            handler = PyTgCalls(client)
            await handler.start()
            VC_SESSIONS[user_id] = handler
        return VC_SESSIONS[user_id]

    # --- 1. SET TARGET (.vctarget @username) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vctarget(?:\s+(.*))?'))
    async def set_target(event):
        target = event.pattern_match.group(1)
        if not target: return await event.edit("❌ **Usage:** `.vctarget @group` ")
        
        try:
            entity = await client.get_entity(target)
            await set_vc_chat(event.sender_id, entity.id)
            await event.edit(f"🎯 **VC Locked:** `{entity.title}`")
        except: await event.edit("❌ **Invalid Group.**")

    # --- 2. STREAM VOICE/AUDIO (.vcstart - Reply to Audio) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstart'))
    async def stream_audio(event):
        reply = await event.get_reply_message()
        if not (reply and (reply.audio or reply.voice)):
            return await event.edit("❌ **Reply to a Voice or Audio file.**")

        chat_id = await get_vc_chat(event.sender_id)
        if not chat_id: return await event.edit("❌ **Set `.vctarget` first.**")

        status = await event.edit("📡 **Preparing Stream...**")
        file_path = f"vc_{event.sender_id}.raw" # Use raw for speed

        try:
            # Download and stream
            path = await client.download_media(reply, file_path)
            call = await get_call_handler(event.sender_id)

            await call.play(chat_id, AudioPiped(path))
            await status.edit("🎙️ **Live on VC!**\nUse `.vcstop` to disconnect.")
        except Exception as e:
            await status.edit(f"❌ **Error:** `{str(e)}` ")

    # --- 3. STOP STREAM (.vcstop) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstop'))
    async def stop_stream(event):
        user_id = event.sender_id
        chat_id = await get_vc_chat(user_id)
        
        if user_id in VC_SESSIONS:
            try:
                await VC_SESSIONS[user_id].leave_call(chat_id)
                # Cleanup temp file
                if os.path.exists(f"vc_{user_id}.raw"): os.remove(f"vc_{user_id}.raw")
                await event.edit("🛑 **Disconnected from VC.**")
            except: await event.edit("⚠️ Already out.")
        else: await event.edit("❌ No active stream.")
