import asyncio
import os
import logging
from telethon import events
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from database import set_vc_chat, get_vc_chat

log = logging.getLogger(__name__)

# Global tracking for active VC sessions
# {user_id: pytgcalls_instance}
VC_SESSIONS = {}

def register(client):

    # --- Helper: Get/Start VC Session ---
    async def get_vc_session(user_id):
        if user_id not in VC_SESSIONS:
            try:
                # Naya instance banao
                session = PyTgCalls(client)
                await session.start()
                VC_SESSIONS[user_id] = session
                log.info(f"🎙️ VC session initialized for {user_id}")
            except Exception as e:
                log.error(f"VC Start Error for {user_id}: {e}")
                return None
        return VC_SESSIONS[user_id]

    # --- 1. SET TARGET GROUP (.vctarget @username) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vctarget(?:\s+(.*))?'))
    async def set_vc_target(event):
        target = event.pattern_match.group(1)
        if not target:
            return await event.edit("❌ **Usage:** `.vctarget @group_username` or Chat ID.")
        
        try:
            # Username/ID ko resolve karo
            entity = await client.get_entity(target)
            await set_vc_chat(event.sender_id, entity.id)
            await event.edit(f"🎯 **VC Destination Locked:** `{entity.title}`\nUse `.vcstart` on an audio file now.")
        except Exception as e:
            await event.edit(f"❌ **Failed to resolve:** `{str(e)}` ")

    # --- 2. START VC STREAM (.vcstart - Reply to Audio) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstart'))
    async def start_vc_stream(event):
        reply = await event.get_reply_message()
        if not (reply and (reply.audio or reply.voice)):
            return await event.edit("❌ **Error:** Please reply to an audio or voice file.")

        chat_id = await get_vc_chat(event.sender_id)
        if not chat_id:
            return await event.edit("❌ **Error:** Set a target group first using `.vctarget` ")

        status = await event.edit("📡 **Syncing with Voice Chat...**")
        
        # Temp file path
        temp_file = f"vc_stream_{event.sender_id}.mp3"
        
        try:
            # Audio download
            await client.download_media(reply, temp_file)
            
            # Start/Get Call Instance
            call = await get_vc_session(event.sender_id)
            if not call:
                return await status.edit("❌ **VC Error:** Calling engine failed to boot.")

            # Play Audio directly
            await call.play(
                chat_id,
                AudioPiped(temp_file)
            )
            
            await status.edit(f"🎙️ **Streaming Live!**\n📍 **Group ID:** `{chat_id}`\n🎶 **Status:** Playing...")
        except Exception as e:
            if os.path.exists(temp_file): os.remove(temp_file)
            await status.edit(f"❌ **Stream Failed:** `{str(e)}` ")

    # --- 3. STOP STREAM (.vcstop) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstop'))
    async def stop_vc_stream(event):
        user_id = event.sender_id
        chat_id = await get_vc_chat(user_id)
        temp_file = f"vc_stream_{user_id}.mp3"

        if user_id in VC_SESSIONS:
            try:
                # Leave Call
                await VC_SESSIONS[user_id].leave_call(chat_id)
                # Cleanup File
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                
                await event.edit("🛑 **VC Stream Stopped.** Memory and cache cleared.")
            except Exception as e:
                await event.edit(f"⚠️ **Note:** Bot left VC with warning: `{e}` ")
        else:
            await event.edit("❌ **No active VC session found.**")
