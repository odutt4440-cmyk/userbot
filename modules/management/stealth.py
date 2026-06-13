import os
import asyncio
from telethon import events, types
from database import get_stealth_settings

# Local cache for Anti-Delete (Last 100 messages)
# Kyunki Telethon delete event me content nahi deta, humein store karna padta hai
MSG_CACHE = {} 

def register(client):

    # --- 1. MESSAGE CACHER (For Anti-Delete) ---
    @client.on(events.NewMessage)
    async def cacher(event):
        if not event.chat_id: return
        # Cache only text and small info
        MSG_CACHE[event.id] = {
            "text": event.text,
            "sender": event.sender_id,
            "chat": event.chat_id,
            "media": event.media if event.media else None
        }
        # Cache cleanup: limit to 100
        if len(MSG_CACHE) > 100:
            first_key = next(iter(MSG_CACHE))
            del MSG_CACHE[first_key]

    # --- 2. SECRET SNATCHER (View-Once Capture) ---
    @client.on(events.NewMessage(incoming=True))
    async def snatcher(event):
        settings = await get_stealth_settings(event.sender_id)
        if not settings.get("snatcher"): return

        # Check for View-Once Media
        is_view_once = False
        if event.photo and getattr(event.photo, 'ttl_seconds', None):
            is_view_once = True
        elif event.video and getattr(event.video, 'ttl_seconds', None):
            is_view_once = True

        if is_view_once:
            sender = await event.get_sender()
            name = sender.first_name if sender else "Unknown"
            
            # Inform in Saved Messages
            await client.send_message("me", f"🕵️ **Secret Snatcher:** Captured a view-once media from **{name}** ({event.sender_id})")
            
            # Download and Send to 'me' (Saved Messages)
            media = await event.download_media()
            await client.send_file("me", media, caption="✅ Recovered Secret Media")
            if os.path.exists(media): os.remove(media)

    # --- 3. ANTI-DELETE ENGINE ---
    @client.on(events.MessageDeleted)
    async def handler(event):
        # Note: sender_id yahan nahi milta, hum har session ke liye settings check karenge
        # Isliye humne MSG_CACHE use kiya hai
        for msg_id in event.deleted_ids:
            if msg_id in MSG_CACHE:
                cached = MSG_CACHE[msg_id]
                
                # Check user setting from DB
                settings = await get_stealth_settings(cached["sender"])
                if not settings.get("antidelete"): return

                log_text = (
                    f"🗑️ **Anti-Delete Detected!**\n"
                    f"👤 **From ID:** `{cached['sender']}`\n"
                    f"💬 **Message:** {cached['text']}"
                )
                await client.send_message("me", log_text)
                
                if cached["media"]:
                    try:
                        await client.send_file("me", cached["media"], caption="📦 Deleted Media Attachment")
                    except: pass
                
                del MSG_CACHE[msg_id]

    # --- 4. COMMANDS TO TOGGLE ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.(snatcher|antidelete) (on|off)'))
    async def stealth_toggle(event):
        feature = event.pattern_match.group(1).lower()
        mode = event.pattern_match.group(2).lower()
        status = 1 if mode == "on" else 0
        
        from database import set_stealth_status
        await set_stealth_status(event.sender_id, feature, status)
        
        await event.edit(f"🕵️ **Stealth Update:** `{feature.upper()}` is now **{mode.upper()}**.")
        await asyncio.sleep(3)
        await event.delete()
