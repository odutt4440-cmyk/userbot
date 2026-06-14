import asyncio
import os
import io
import logging
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
from telethon import events, functions, types, errors
from database import save_user_pack, get_pack_short_name

log = logging.getLogger(__name__)

# --- 🛠️ GLOBAL TRACKER ---
PROCESSED_EVENTS = set()

# --- 🛠️ HELPERS ---

async def safe_edit(event, text, **kwargs):
    try:
        return await event.edit(text, **kwargs)
    except Exception:
        return event

def is_ffmpeg_installed():
    return shutil.which("ffmpeg") is not None

def prepare_static_sticker(image_bytes):
    try:
        if not image_bytes: return None
        img = Image.open(io.BytesIO(image_bytes))
        if getattr(img, "is_animated", False):
            img.seek(0)
        img = img.convert("RGBA")
        width, height = img.size
        if width > height:
            new_width, new_height = 512, int(512 * (height / width))
        else:
            new_height, new_width = 512, int(512 * (width / height))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return out
    except: return None

def draw_meme_text(image, top_text, bottom_text):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    # Bada Font Size
    font_size = int(height / 7) 
    if font_size < 35: font_size = 40
    
    try:
        fpath = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(fpath, font_size) if os.path.exists(fpath) else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    def draw_bold_text(text, y_pos):
        if not text: return
        w = draw.textlength(text, font=font) if hasattr(draw, 'textlength') else 100
        x = (width - w) / 2
        # Outline logic (Bada aur Bold)
        outline_range = 4
        for ox in range(-outline_range, outline_range + 1):
            for oy in range(-outline_range, outline_range + 1):
                draw.text((x + ox, y_pos + oy), text, font=font, fill="black")
        draw.text((x, y_pos), text, font=font, fill="white")

    if top_text:
        draw_bold_text(top_text, 20)
    if bottom_text:
        draw_bold_text(bottom_text, height - font_size - 30)
    return image

async def refresh_pack(client, short_name):
    try:
        await client(functions.messages.GetStickerSetRequest(
            stickerset=types.InputStickerSetShortName(short_name=short_name), hash=0
        ))
    except: pass

def register(client):

    # --- 1. KANG COMMAND (.kang [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.kang(?:\s+([\w\s]+))?(?:\s+(.+))?'))
    async def kang_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        if not event.is_reply: return await safe_edit(event, "❌ Reply to media.")
        reply = await event.get_reply_message()
        pack_arg = event.pattern_match.group(1)
        emoji = event.pattern_match.group(2) or "⚡"
        pack_name = pack_arg.strip() if pack_arg else "EmpirePack"
        status = await safe_edit(event, f"✨ **Creating Pack `{pack_name}`...**")
        try:
            is_anim = reply.file.ext == '.tgs'
            is_video = reply.file.mime_type == 'video/webm'
            media_bytes = await client.download_media(reply, bytes)
            if not is_anim and not is_video:
                sticker_io = prepare_static_sticker(media_bytes)
                sticker_io.name = "sticker.png"
            else:
                sticker_io = io.BytesIO(media_bytes)
                sticker_io.name = "sticker.tgs" if is_anim else "sticker.webm"
            sent_msg = await client.send_file('me', sticker_io, force_document=True)
            doc = sent_msg.media.document
            sticker_item = types.InputStickerSetItem(
                document=types.InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference),
                emoji=emoji
            )
            me = await client.get_me()
            short_name = f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
            await client(functions.stickers.CreateStickerSetRequest(user_id=me.id, title=pack_name, short_name=short_name, stickers=[sticker_item]))
            await save_user_pack(me.id, pack_name, short_name)
            await safe_edit(status, f"✅ **Pack Created!**\n🔗 https://t.me/addstickers/{short_name}")
            await sent_msg.delete()
            await refresh_pack(client, short_name)
        except Exception as e:
            if "SHORTNAME_OCCUPIED" in str(e): await safe_edit(status, f"❌ Pack exists. Use `.add {pack_name}`.")
            else: await safe_edit(status, f"❌ Error: {str(e)}")

    # --- 2. ADD COMMAND (.add [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.add(?:\s+([\w\s]+))?(?:\s+(.+))?'))
    async def add_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        if not event.is_reply: return await safe_edit(event, "❌ Reply to media.")
        pack_arg = event.pattern_match.group(1)
        if not pack_arg: return await safe_edit(event, "❌ Usage: `.add PackName` ")
        pack_name = pack_arg.strip()
        emoji = event.pattern_match.group(2) or "⚡"
        reply = await event.get_reply_message()
        status = await safe_edit(event, f"🚀 **Adding to `{pack_name}`...**")
        try:
            me = await client.get_me()
            short_name = await get_pack_short_name(me.id, pack_name) or f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
            is_anim = reply.file.ext == '.tgs'
            is_video = reply.file.mime_type == 'video/webm'
            media_bytes = await client.download_media(reply, bytes)
            if not is_anim and not is_video:
                sticker_io = prepare_static_sticker(media_bytes)
                sticker_io.name = "sticker.png"
            else:
                sticker_io = io.BytesIO(media_bytes)
                sticker_io.name = "sticker.tgs" if is_anim else "sticker.webm"
            sent_msg = await client.send_file('me', sticker_io, force_document=True)
            doc = sent_msg.media.document
            await client(functions.stickers.AddStickerToSetRequest(stickerset=types.InputStickerSetShortName(short_name=short_name), sticker=types.InputStickerSetItem(document=types.InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference), emoji=emoji)))
            await safe_edit(status, f"✅ **Added!**\n🔗 https://t.me/addstickers/{short_name}")
            await sent_msg.delete()
            await refresh_pack(client, short_name)
        except Exception as e: await safe_edit(status, f"❌ Failed: {str(e)}")

    # --- 3. DELETE STICKER ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delsticker(?:\s+(.*))?'))
    async def remove_sticker_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        if not event.is_reply: return await safe_edit(event, "❌ Reply to sticker.")
        status = await safe_edit(event, "🗑️ **Removing...**")
        try:
            reply = await event.get_reply_message()
            await client(functions.stickers.RemoveStickerFromSetRequest(sticker=types.InputDocument(id=reply.media.document.id, access_hash=reply.media.document.access_hash, file_reference=reply.media.document.file_reference)))
            await safe_edit(status, "✅ **Removed!**")
        except Exception as e: await safe_edit(status, f"❌ Failed: {str(e)}")

    # --- 4. MEMIFY COMMAND (Static & Animated Fixed) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.mm(?:\s+(.*))?'))
    async def memify_handler(event):
        if not event.is_reply: 
            return await safe_edit(event, "❌ **Error:** Reply to media.")
        
        args = event.pattern_match.group(1)
        if not args or ";" not in args:
            return await safe_edit(event, "❌ **Usage:** `.mm TOP TEXT ; BOTTOM TEXT` ")

        parts = args.split(";", 1)
        top = parts[0].strip().upper()
        bottom = parts[1].strip().upper() if len(parts) > 1 else ""

        reply = await event.get_reply_message()
        status = await safe_edit(event, "🎨 **Creating Meme...**")
        
        try:
            is_video = reply.file.mime_type == 'video/webm'
            is_anim = reply.file.ext == '.tgs'

            if (is_video or is_anim) and is_ffmpeg_installed():
                # --- ANIMATED MEMIFY ---
                input_file = await client.download_media(reply, f"mm_in_{event.id}")
                output_file = f"mm_out_{event.id}.webm"
                fpath = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                
                # FFmpeg Command Construction
                filter_chain = []
                if top:
                    filter_chain.append(f"drawtext=fontfile='{fpath}':text='{top}':fontcolor=white:fontsize=45:borderw=3:bordercolor=black:x=(w-text_w)/2:y=20")
                if bottom:
                    filter_chain.append(f"drawtext=fontfile='{fpath}':text='{bottom}':fontcolor=white:fontsize=45:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-th-30")
                
                cmd = ["ffmpeg", "-i", input_file, "-vf", ",".join(filter_chain), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-y", output_file]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                await client.send_file(event.chat_id, output_file, reply_to=reply.id)
                for f in [input_file, output_file]:
                    if os.path.exists(f): os.remove(f)
            else:
                # --- STATIC MEMIFY ---
                img_data = await client.download_media(reply, bytes)
                image = Image.open(io.BytesIO(img_data)).convert("RGBA")
                meme_img = draw_meme_text(image, top, bottom)
                output = io.BytesIO()
                meme_img.save(output, format="WEBP")
                output.seek(0)
                await client.send_file(event.chat_id, output, reply_to=reply.id)

            await status.delete()
        except Exception as e:
            log.error(f"Memify Error: {e}")
            await safe_edit(status, "❌ **Memify Failed. Ensure FFmpeg is installed.**")

    # --- 5. PACK LINK ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.pack(?:\s+(.*))?'))
    async def pack_handler(event):
        pack_name = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else "EmpirePack"
        me = await client.get_me()
        sn = await get_pack_short_name(me.id, pack_name) or f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
        await safe_edit(event, f"📦 **Pack:** `{pack_name}`\n🔗 https://t.me/addstickers/{sn}")

    # --- 6. DELETE PACK ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delpack(?:\s+(.*))?'))
    async def delete_pack_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        pack_name = event.pattern_match.group(1)
        if not pack_name: return await safe_edit(event, "❌ Specify Pack Name.")
        status = await safe_edit(event, f"⚠️ **Deleting `{pack_name}`...**")
        try:
            me = await client.get_me()
            sn = await get_pack_short_name(me.id, pack_name) or f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
            await client(functions.stickers.DeleteStickerSetRequest(stickerset=types.InputStickerSetShortName(short_name=sn)))
            from database import db
            await db["sticker_packs"].delete_one({"user_id": me.id, "pack_name": pack_name.lower()})
            await safe_edit(status, f"🗑️ **Pack Deleted.**")
        except Exception as e: await safe_edit(status, f"❌ Failed: {str(e)}")
