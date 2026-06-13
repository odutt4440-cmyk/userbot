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
    except errors.MessageNotModifiedError:
        return event
    except Exception as e:
        log.error(f"Edit Error: {e}")
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
        log.error(f"Prepare Static Error: {e}")
        return None

def draw_text(image, top_text, bottom_text):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    try:
        # Standard Linux path for Railway
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

    # --- 1. KANG COMMAND (.kang [packname] [emoji]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.kang(?:\s+([\w\s]+))?(?:\s+(.+))?'))
    async def kang_handler(event):
        if not event.is_reply:
            return await safe_edit(event, "❌ **Error:** Reply to a media file.")
        
        reply = await event.get_reply_message()
        pack_arg = event.pattern_match.group(1)
        emoji = event.pattern_match.group(2) or "⚡"
        
        # Detection
        is_anim = False
        is_video = False
        if reply.document:
            if reply.document.mime_type == 'application/x-tgsticker': is_anim = True
            elif reply.document.mime_type == 'video/webm': is_video = True
        
        base_name = pack_arg.strip() if pack_arg else "EmpirePack"
        # Type-based naming ensures no mixed-pack errors from Telegram
        if is_anim: pack_name_raw = f"{base_name}_Anim"
        elif is_video: pack_name_raw = f"{base_name}_Video"
        else: pack_name_raw = base_name

        status = await safe_edit(event, f"⚡ **Kanging {('Animation' if is_anim else 'Video' if is_video else 'Sticker')}...**")
        
        try:
            media_bytes = await client.download_media(reply, bytes)
            if not is_anim and not is_video:
                sticker_io = prepare_static_sticker(media_bytes)
                if not sticker_io: return await safe_edit(status, "❌ **Process Failed.**")
                sticker_io.name = "sticker.png"
            else:
                sticker_io = io.BytesIO(media_bytes)
                sticker_io.name = "sticker.tgs" if is_anim else "sticker.webm"

            sent_msg = await client.send_file('me', sticker_io, force_document=True)
            raw_doc = sent_msg.media.document
            sticker_item = types.InputStickerSetItem(
                document=types.InputDocument(id=raw_doc.id, access_hash=raw_doc.access_hash, file_reference=raw_doc.file_reference), 
                emoji=emoji
            )

            me = await client.get_me()
            short_name = await get_pack_short_name(me.id, pack_name_raw)
            constructed_sn = f"{pack_name_raw.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
            
            try:
                if not short_name:
                    await safe_edit(status, f"✨ **Creating Pack:** `{pack_name_raw}`...")
                    # Minimum arguments to avoid version conflicts
                    await client(functions.stickers.CreateStickerSetRequest(
                        user_id=me.id,
                        title=pack_name_raw,
                        short_name=constructed_sn,
                        stickers=[sticker_item]
                    ))
                    await save_user_pack(me.id, pack_name_raw, constructed_sn)
                    short_name = constructed_sn
                else:
                    await client(functions.stickers.AddStickerToSetRequest(
                        stickerset=types.InputStickerSetShortName(short_name=short_name),
                        sticker=sticker_item
                    ))
                
                await safe_edit(status, f"✅ **Added to `{pack_name_raw}`!**\n🔗 https://t.me/addstickers/{short_name}")
            except Exception as e:
                # Sync logic if Telegram has it but DB doesn't
                if "SHORTNAME_OCCUPIED" in str(e) or "STICKERSET_INVALID" in str(e):
                    await client(functions.stickers.AddStickerToSetRequest(
                        stickerset=types.InputStickerSetShortName(short_name=constructed_sn),
                        sticker=sticker_item
                    ))
                    await save_user_pack(me.id, pack_name_raw, constructed_sn)
                    await safe_edit(status, f"✅ **Synced & Added!**\n🔗 https://t.me/addstickers/{constructed_sn}")
                else: raise e

            await sent_msg.delete()
        except Exception as e:
            log.error(f"Kang Error: {e}")
            await safe_edit(status, f"❌ **Error:** Pack operation failed.")

    # --- 2. DELETE STICKER (.delsticker [packname]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delsticker(?:\s+(.*))?'))
    async def remove_sticker_handler(event):
        if not event.is_reply: return await safe_edit(event, "❌ Reply to the sticker to remove.")
        pack_name = event.pattern_match.group(1)
        if not pack_name: return await safe_edit(event, "❌ **Usage:** `.delsticker PackName` (Reply to sticker)")
        
        reply = await event.get_reply_message()
        if not reply.media or not hasattr(reply.media, 'document'):
             return await safe_edit(event, "❌ Not a valid sticker.")

        status = await safe_edit(event, f"🗑️ **Removing from `{pack_name}`...**")
        try:
            # We use the Document ID directly, Telegram knows the set
            await client(functions.stickers.RemoveStickerFromSetRequest(
                sticker=types.InputDocument(
                    id=reply.media.document.id, 
                    access_hash=reply.media.document.access_hash, 
                    file_reference=reply.media.document.file_reference
                )
            ))
            await safe_edit(status, f"✅ **Sticker removed from `{pack_name}`!**")
        except Exception as e:
            log.error(f"DelSticker Error: {e}")
            await safe_edit(status, "❌ **Failed:** Could not remove sticker.")

    # --- 3. DELETE FULL PACK (.delpack [packname]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delpack(?:\s+(.*))?'))
    async def delete_full_pack_handler(event):
        pack_name = event.pattern_match.group(1)
        if not pack_name: return await safe_edit(event, "❌ Usage: `.delpack Name` ")
        
        status = await safe_edit(event, f"⚠️ **Deleting full pack `{pack_name}`...**")
        try:
            me = await client.get_me()
            short_name = await get_pack_short_name(me.id, pack_name.strip())
            
            # Construct if not in DB
            if not short_name:
                short_name = f"{pack_name.replace(' ', '_').strip()}_{me.id}_by_{me.username or me.id}"

            # Delete request
            await client(functions.stickers.DeleteStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=short_name)
            ))
            
            # DB Cleanup
            from database import db
            if db is not None:
                await db["sticker_packs"].delete_one({"user_id": me.id, "pack_name": pack_name.lower().strip()})
            
            await safe_edit(status, f"🗑️ **Pack `{pack_name}` deleted successfully.**")
        except Exception as e:
            log.error(f"DelPack Error: {e}")
            await safe_edit(status, "❌ **Failed:** Could not delete pack from Telegram.")

    # --- 4. MEMIFY & PACK LINK (Same) ---
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
        except Exception as e: await safe_edit(status, f"❌ Memify failed.")

    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.pack(?:\s+(.*))?'))
    async def pack_handler(event):
        pack_name = event.pattern_match.group(1).strip() if event.pattern_match.group(1) else "EmpirePack"
        me = await client.get_me()
        sn = await get_pack_short_name(me.id, pack_name)
        if not sn: sn = f"{pack_name.replace(' ', '_')}_{me.id}_by_{me.username or me.id}"
        await safe_edit(event, f"📦 **Pack:** `{pack_name}`\n🔗 https://t.me/addstickers/{sn}")
