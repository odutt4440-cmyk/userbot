import asyncio
import os
import io
import logging
import subprocess
import shutil
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

def prepare_static_sticker(image_bytes):
    try:
        if not image_bytes: return None
        img = Image.open(io.BytesIO(image_bytes))
        if getattr(img, "is_animated", False):
            img.seek(0)
            img = img.convert("RGBA")
        if img.mode != 'RGBA': img = img.convert('RGBA')
        
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
    except Exception as e:
        log.error(f"Image Prep Error: {e}")
        return None

async def refresh_pack(client, short_name):
    try:
        await client(functions.messages.GetStickerSetRequest(
            stickerset=types.InputStickerSetShortName(short_name=short_name),
            hash=0
        ))
    except: pass

def is_ffmpeg():
    return shutil.which("ffmpeg") is not None or os.path.exists("/usr/bin/ffmpeg")

async def convert_to_webm(input_path, output_path):
    if not is_ffmpeg(): return False
    # Target scale to exact 512 with padding for telegram specs
    cmd = [
        "ffmpeg", "-i", input_path, "-t", "3", "-vf",
        "scale=512:512:force_original_aspect_ratio=decrease,format=rgba,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=#00000000",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-an", "-y", output_path
    ]
    process = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process.returncode == 0

def draw_meme(image, top, bottom):
    draw = ImageDraw.Draw(image)
    w, h = image.size
    fs = int(h / 8) if h > 0 else 40
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    font = None
    for path in font_paths:
        if os.path.exists(path):
            font = ImageFont.truetype(path, fs)
            break
    if not font:
        font = ImageFont.load_default()

    def draw_t(txt, y):
        if not txt: return
        tw = draw.textlength(txt, font=font) if hasattr(draw, 'textlength') else len(txt) * (fs * 0.6)
        x = (w - tw) / 2
        for o in range(-2, 3):
            for oy in range(-2, 3): 
                draw.text((x+o, y+oy), txt, font=font, fill="black")
        draw.text((x, y), txt, font=font, fill="white")
        
    if top:
        draw_t(top, 15)
    if bottom:
        draw_t(bottom, h - fs - 25)
    return image

def register(client):

    # --- 1. KANG & ADD ROUTER ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.(kang|add)(?:\s+([\w\s]+))?(?:\s+(.+))?'))
    async def kang_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        if not event.is_reply: return await safe_edit(event, "❌ Reply to media.")
        
        cmd = event.pattern_match.group(1).lower()
        pack_arg = event.pattern_match.group(2)
        emoji = event.pattern_match.group(3) or "⚡"
        pack_name = pack_arg.strip() if pack_arg else "EmpirePack"
        
        reply = await event.get_reply_message()
        status = await safe_edit(event, f"⚡ **Processing {cmd.upper()}...**")
        
        try:
            me = await client.get_me()
            is_anim = reply.file.ext == '.tgs'
            is_video = (reply.file.mime_type in ['video/webm', 'video/mp4', 'image/gif']) or (reply.file.ext in ['.webm', '.mp4', '.gif'])
            
            media_path = await client.download_media(reply, f"temp_{event.id}")
            sticker_io = io.BytesIO()

            if is_anim:
                with open(media_path, 'rb') as f: sticker_io.write(f.read())
                sticker_io.name = "sticker.tgs"
            elif is_video:
                if not is_ffmpeg(): 
                    if os.path.exists(media_path): os.remove(media_path)
                    return await safe_edit(status, "❌ FFmpeg missing on server. Buildpack add karo.")
                webm_path = f"temp_{event.id}.webm"
                if await convert_to_webm(media_path, webm_path):
                    with open(webm_path, 'rb') as f: sticker_io.write(f.read())
                    sticker_io.name = "sticker.webm"
                    if os.path.exists(webm_path): os.remove(webm_path)
                else: 
                    if os.path.exists(media_path): os.remove(media_path)
                    return await safe_edit(status, "❌ Conversion failed.")
            else:
                with open(media_path, 'rb') as f:
                    res = prepare_static_sticker(f.read())
                    sticker_io = res
                    sticker_io.name = "sticker.png"

            if os.path.exists(media_path): os.remove(media_path)
            sticker_io.seek(0)
            
            sent = await client.send_file('me', sticker_io, force_document=True)
            doc = sent.media.document
            sticker_item = types.InputStickerSetItem(
                document=types.InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference), 
                emoji=emoji
            )

            sn = await get_pack_short_name(me.id, pack_name) or f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
            
            if cmd == "kang":
                try:
                    await client(functions.stickers.CreateStickerSetRequest(user_id=me.id, title=pack_name, short_name=sn, stickers=[sticker_item]))
                    await save_user_pack(me.id, pack_name, sn)
                except errors.errors.ShortnameOccupiedError:
                    cmd = "add"
            
            if cmd == "add":
                await client(functions.stickers.AddStickerToSetRequest(stickerset=types.InputStickerSetShortName(short_name=sn), sticker=sticker_item))
            
            await safe_edit(status, f"✅ **Processed successfully!**\n🔗 https://t.me/addstickers/{sn}")
            await sent.delete()
            await refresh_pack(client, sn)
        except Exception as e: await safe_edit(status, f"❌ Error: {str(e)}")

    # --- 2. DELETE STICKER ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delsticker(?:\s+(.*))?'))
    async def remove_sticker_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        if not event.is_reply: return await safe_edit(event, "❌ Reply to sticker.")
        
        status = await safe_edit(event, "🗑️ **Removing sticker...**")
        try:
            reply = await event.get_reply_message()
            await client(functions.stickers.RemoveStickerFromSetRequest(
                sticker=types.InputDocument(id=reply.media.document.id, access_hash=reply.media.document.access_hash, file_reference=reply.media.document.file_reference)
            ))
            await safe_edit(status, "✅ **Removed from pack!**")
        except Exception as e:
            if "STICKERSET_INVALID" in str(e) or "NOT_MODIFIED" in str(e):
                await safe_edit(status, "✅ **Sticker deleted.**")
            else:
                await safe_edit(status, f"❌ Failed: {str(e)}")

    # --- 3. DELETE PACK ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delpack(?:\s+(.*))?'))
    async def delete_pack_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        pack_arg = event.pattern_match.group(1)
        if not pack_arg: return await safe_edit(event, "❌ Specify Pack Name.")
        
        pack_name = pack_arg.strip()
        status = await safe_edit(event, f"⚠️ **Deleting Pack `{pack_name}`...**")
        try:
            me = await client.get_me()
            short_name = await get_pack_short_name(me.id, pack_name)
            if not short_name:
                short_name = f"{pack_name.replace(' ', '_').strip()}_{me.id}_by_{me.username or me.id}"

            try:
                await client(functions.stickers.DeleteStickerSetRequest(stickerset=types.InputStickerSetShortName(short_name=short_name)))
            except: pass

            from database import db
            if db is not None:
                await db["sticker_packs"].delete_one({"user_id": me.id, "pack_name": pack_name.lower()})
            await safe_edit(status, f"🗑️ **Pack `{pack_name}` deleted successfully.**")
        except Exception as e: await safe_edit(status, f"❌ **Failed:** {str(e)}")

    # --- 4. PACK LINK ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.pack(?:\s+(.*))?'))
    async def pack_handler(event):
        pack_name = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else "EmpirePack"
        me = await client.get_me()
        sn = await get_pack_short_name(me.id, pack_name)
        if not sn: sn = f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
        await safe_edit(event, f"📦 **Pack:** `{pack_name}`\n🔗 https://t.me/addstickers/{sn}")

    # --- 5. THE ULTIMATE MEMIFY COMMAND ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.mm(?:\s+(.*))?'))
    async def memify_handler(event):
        if event.id in PROCESSED_EVENTS: return
        PROCESSED_EVENTS.add(event.id)
        if not event.is_reply: return await safe_edit(event, "❌ Reply to a photo or sticker.")
        
        args = event.pattern_match.group(1)
        if not args: return await safe_edit(event, "❌ Usage: `.mm Top ; Bottom` ya sirf `.mm Top` ")
        
        # Safe splitting for handling single text or both texts
        if ";" in args:
            parts = args.split(";", 1)
            top = parts[0].strip().upper()
            bottom = parts[1].strip().upper()
        else:
            top = args.strip().upper()
            bottom = ""
            
        reply = await event.get_reply_message()
        status = await safe_edit(event, "🎨 **Creating Meme Sticker...**")
        
        try:
            is_video_sticker = reply.file.mime_type == 'video/webm' or (reply.file.ext == '.webm') or (reply.file.mime_type in ['video/mp4', 'image/gif'])
            is_anim_tgs = reply.file.ext == '.tgs'
            
            # CASE A: Video/WebM Animated Sticker Modding via FFmpeg
            if is_video_sticker and is_ffmpeg():
                fpath = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if not os.path.exists(fpath):
                    fpath = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
                
                in_f = await client.download_media(reply, f"mm_in_{event.id}.webm")
                out_f = f"mm_out_{event.id}.webm"
                
                # Fixed FFmpeg filter variables and logic
                filters = ["scale=512:512"]
                if top:
                    filters.append(f"drawtext=fontfile='{fpath}':text='{top}':fontcolor=white:fontsize=40:borderw=4:bordercolor=black:x=(w-text_w)/2:y=25")
                if bottom:
                    # 'th' replaced with a static 40 for safety to avoid crash
                    filters.append(f"drawtext=fontfile='{fpath}':text='{bottom}':fontcolor=white:fontsize=40:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-40-35")
                
                filt = ",".join(filters)
                
                cmd = ["ffmpeg", "-i", in_f, "-vf", filt, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-an", "-y", out_f]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                await client.send_file(event.chat_id, out_f, reply_to=reply.id, as_sticker=True)
                for f in [in_f, out_f]: 
                    if os.path.exists(f): os.remove(f)
                    
            # CASE B: Standard Static Images or Fallback TGS Snapshot
            else:
                img_data = await client.download_media(reply, bytes, thumb=-1 if is_anim_tgs else None)
                if not img_data:
                    return await safe_edit(status, "❌ Media data context structure unreadable.")
                    
                image = Image.open(io.BytesIO(img_data)).convert("RGBA")
                processed_image = prepare_static_sticker(img_data)
                if processed_image:
                    image = Image.open(processed_image).convert("RGBA")
                
                meme_img = draw_meme(image, top, bottom)
                output = io.BytesIO()
                meme_img.save(output, format="WEBP", method=6)
                output.seek(0)
                
                await client.send_file(event.chat_id, output, reply_to=reply.id, as_sticker=True)
                
            await status.delete()
        except Exception as e: 
            await safe_edit(status, f"❌ Failed: {str(e)}")
