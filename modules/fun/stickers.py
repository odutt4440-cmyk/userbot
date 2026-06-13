import asyncio
import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont
from telethon import events, functions, types, errors
from database import save_user_pack, get_pack_short_name

log = logging.getLogger(__name__)

# --- 🛠️ HELPERS ---

async def safe_edit(event, text, **kwargs):
    try:
        return await event.edit(text, **kwargs)
    except Exception:
        return event

def prepare_static_sticker(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
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
    except: return None

def draw_text(image, top_text, bottom_text):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(height/10))
    except: font = ImageFont.load_default()
    def draw_styled_text(text, pos):
        draw.text((pos[0]-2, pos[1]-2), text, font=font, fill="black")
        draw.text((pos[0]+2, pos[1]-2), text, font=font, fill="black")
        draw.text(pos, text, font=font, fill="white")
    if top_text:
        tw = draw.textlength(top_text, font=font) if hasattr(draw, 'textlength') else 100
        draw_styled_text(top_text, ((width-tw)/2, 10))
    if bottom_text:
        tw = draw.textlength(bottom_text, font=font) if hasattr(draw, 'textlength') else 100
        draw_styled_text(bottom_text, ((width-tw)/2, height - height/8))
    return image

def register(client):

    # --- 1. KANG COMMAND (.kang [name]) - CREATE ONLY ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.kang(?:\s+([\w\s]+))?(?:\s+(.+))?'))
    async def kang_handler(event):
        if not event.is_reply:
            return await safe_edit(event, "❌ **Error:** Reply to media to create a pack.")
        
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
            
            await client(functions.stickers.CreateStickerSetRequest(
                user_id=me.id, title=pack_name, short_name=short_name, stickers=[sticker_item]
            ))
            
            await save_user_pack(me.id, pack_name, short_name)
            await safe_edit(status, f"✅ **Pack Created!**\n🔗 https://t.me/addstickers/{short_name}\n👉 Use `.add {pack_name}` for more.")
            await sent_msg.delete()

        except Exception as e:
            if "SHORTNAME_OCCUPIED" in str(e):
                await safe_edit(status, f"❌ **Error:** Pack `{pack_name}` already exists.\n👉 Use `.add {pack_name}` instead.")
            else:
                await safe_edit(status, f"❌ **Error:** {str(e)}")

    # --- 2. ADD COMMAND (.add [name]) - ADD TO EXISTING ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.add(?:\s+([\w\s]+))?(?:\s+(.+))?'))
    async def add_handler(event):
        if not event.is_reply:
            return await safe_edit(event, "❌ Reply to media + specify pack name.")
        
        pack_arg = event.pattern_match.group(1)
        if not pack_arg:
            return await safe_edit(event, "❌ **Usage:** `.add PackName` ")

        pack_name = pack_arg.strip()
        emoji = event.pattern_match.group(2) or "⚡"
        reply = await event.get_reply_message()
        status = await safe_edit(event, f"🚀 **Adding to `{pack_name}`...**")
        
        try:
            me = await client.get_me()
            short_name = await get_pack_short_name(me.id, pack_name)
            if not short_name:
                short_name = f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"

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

            await client(functions.stickers.AddStickerToSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=short_name),
                sticker=sticker_item
            ))
            
            await safe_edit(status, f"✅ **Added to `{pack_name}`!**\n🔗 https://t.me/addstickers/{short_name}")
            await sent_msg.delete()

        except Exception as e:
            await safe_edit(status, f"❌ **Failed:** {str(e)}")

    # --- 3. DELETE STICKER (.delsticker [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delsticker(?:\s+(.*))?'))
    async def remove_sticker_handler(event):
        if not event.is_reply: return await safe_edit(event, "❌ Reply to sticker.")
        pack_name = event.pattern_match.group(1) or "Pack"
        
        status = await safe_edit(event, f"🗑️ **Removing from `{pack_name}`...**")
        try:
            reply = await event.get_reply_message()
            await client(functions.stickers.RemoveStickerFromSetRequest(
                sticker=types.InputDocument(id=reply.media.document.id, access_hash=reply.media.document.access_hash, file_reference=reply.media.document.file_reference)
            ))
            await safe_edit(status, f"✅ **Sticker removed from `{pack_name}`!**")
        except Exception as e:
            if "STICKERSET_NOT_MODIFIED" in str(e):
                await safe_edit(status, f"✅ **Success:** Sticker already removed from `{pack_name}`.")
            else:
                await safe_edit(status, f"❌ **Failed:** {str(e)}")

    # --- 4. DELETE PACK (.delpack [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delpack(?:\s+(.*))?'))
    async def delete_pack_handler(event):
        pack_arg = event.pattern_match.group(1)
        if not pack_arg: return await safe_edit(event, "❌ Specify Pack Name.")
        
        pack_name = pack_arg.strip()
        status = await safe_edit(event, f"⚠️ **Deleting Pack `{pack_name}`...**")
        try:
            me = await client.get_me()
            short_name = await get_pack_short_name(me.id, pack_name)
            if not short_name:
                short_name = f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"

            try:
                await client(functions.stickers.DeleteStickerSetRequest(stickerset=types.InputStickerSetShortName(short_name=short_name)))
            except Exception as e:
                if "INVALID" not in str(e).upper(): raise e

            from database import db
            if db is not None:
                await db["sticker_packs"].delete_one({"user_id": me.id, "pack_name": pack_name.lower()})
            
            await safe_edit(status, f"🗑️ **Pack `{pack_name}` deleted successfully.**")
        except Exception as e:
            await safe_edit(status, f"❌ **Failed:** {str(e)}")

    # --- 5. PACK LINK (.pack [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.pack(?:\s+(.*))?'))
    async def pack_handler(event):
        pack_name = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else "EmpirePack"
        me = await client.get_me()
        sn = await get_pack_short_name(me.id, pack_name)
        if not sn: sn = f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
        await safe_edit(event, f"📦 **Pack:** `{pack_name}`\n🔗 https://t.me/addstickers/{sn}")

    # --- 6. MEMIFY ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.mm(?:\s+(.*))?'))
    async def memify_handler(event):
        if not event.is_reply: return await safe_edit(event, "❌ Reply to media.")
        text = event.pattern_match.group(1)
        if not text or ";" not in text: return await safe_edit(event, "❌ Usage: `.mm TOP ; BOTTOM` ")
        
        top, bottom = (text.split(";") + [""])[:2]
        status = await safe_edit(event, "🎨 **Memifying...**")
        img_data = await client.download_media(await event.get_reply_message(), bytes)
        try:
            image = Image.open(io.BytesIO(img_data)).convert("RGBA")
            meme_img = draw_text(image, top.strip().upper(), bottom.strip().upper())
            output = io.BytesIO()
            meme_img.save(output, format="WEBP")
            output.seek(0)
            await client.send_file(event.chat_id, output, reply_to=(await event.get_reply_message()).id)
            await status.delete()
        except Exception: await safe_edit(status, f"❌ Memify failed.")
