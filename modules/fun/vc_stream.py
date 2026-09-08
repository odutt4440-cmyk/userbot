import asyncio
import os
import logging
from telethon import events
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from database import set_vc_chat, get_vc_chat

log = logging.getLogger(__name__)

# Global Dict to manage multiple userbot VC sessions
VC_INSTANCES = {} # {user_id: pytgcalls_client}

def register(client):

    # --- Helper: Get/Start VC Instance for this session ---
    async def get_vc(user_id):
        if user_id not in VC_INSTANCES:
            vc = PyTgCalls(client)
            await vc.start()
            VC_INSTANCES[user_id] = vc
        return VC_INSTANCES[user_id]

    # --- 1. SET TARGET GROUP (.vctarget [username/id]) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vctarget(?:\s+(.*))?'))
    async def set_target(event):
        target = event.pattern_match.group(1)
        if not target:
            return await event.edit("❌ **Usage:** `.vctarget @group_username` or Chat ID.")
        
        try:
            entity = await client.get_entity(target)
            await set_vc_chat(event.sender_id, entity.id)
            await event.edit(f"🎯 **VC Target Set:** `{entity.title}` (`{entity.id}`)\nNow reply to any audio with `.vcstart` to stream.")
        except Exception as e:
            await event.edit(f"❌ **Error:** Could not resolve chat. `{str(e)}` ")

    # --- 2. START STREAM (.vcstart - Reply to Audio) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstart'))
    async def start_stream(event):
        reply = await event.get_reply_message()
        if not (reply and (reply.audio or reply.voice)):
            return await event.edit("❌ **Error:** Reply to an audio file or voice message.")

        chat_id = await get_vc_chat(event.sender_id)
        if not chat_id:
            return await event.edit("❌ **Error:** Target group not set. Use `.vctarget` first.")

        status = await event.edit("📡 **Downloading & preparing stream...**")
        
        # Audio File Path
        file_path = f"stream_{event.sender_id}.mp3"
        
        try:
            # Download audio
            await client.download_media(reply, file_path)
            vc = await get_vc(event.sender_id)

            # Join and Play (High Quality Piped)
            await vc.play(
                chat_id,
                AudioPiped(file_path)
            )
            
            await status.edit(f"🎙️ **Live on VC!**\n📍 **Chat ID:** `{chat_id}`\n🎶 **Playing:** `{reply.file.name or 'Voice Message'}`\n\n_Note: Use `.vcstop` to end and delete files._")
        except Exception as e:
            if os.path.exists(file_path): os.remove(file_path)
            await status.edit(f"❌ **VC Stream Failed:** `{str(e)}` ")

    # --- 3. STOP & CLEANUP (.vcstop) ---
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstop'))
    async def stop_stream(event):
        user_id = event.sender_id
        chat_id = await get_vc_chat(user_id)
        file_path = f"stream_{user_id}.mp3"

        if user_id in VC_INSTANCES:
            try:
                # Leave VC
                await VC_INSTANCES[user_id].leave_call(chat_id)
                # Cleanup File
                if os.path.exists(file_path): os.remove(file_path)
                
                await event.edit("🛑 **VC Session Terminated.** Temporary files deleted.")
            except Exception as e:
                await event.edit(f"⚠️ **Note:** Bot left VC, but encountered error: `{e}` ")
        else:
            await event.edit("❌ **No active VC session found.**")
