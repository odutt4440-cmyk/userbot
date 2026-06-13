import asyncio
import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont
from telethon import events, functions, types, errors
from database import save_user_pack, get_pack_short_name

log = logging.getLogger(__name__)

# --- 🛠️ HELPER: RESIZE & CONVERT TO PNG ---
def prepare_sticker(image_bytes):
    try:
        if not image_bytes:
            return None
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        width, height = img.size
        if width > height:
            new_width = 512
            new_height = int(512 * (height / width))
        else:
            new_height = 512
            new_width = int(512 * (width / height))
            
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return out
    except Exception as e:
        log.error(f"Image Prep Error: {e}")
        return None

# --- 🎨 HELPER: DRAW TEXT FOR MEMIFY ---
def draw_text(image, top_text, bottom_text):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, int(height/10)) if os.path.exists(font_path) else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    def draw_styled_text(text, position):
        draw.text((position[0]-2, position[1]-2), text, font=font, fill="black")
        draw.text((position[0]+2, position[1]-2), text, font=font, fill="black")
        draw.text((position[0]-2, position[1]+2), text, font=font, fill="black")
        draw.text((position[0]+2, position[1]+2), text, font=font, fill="black")
        draw.text(position, text, font=font, fill="white")

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
            return await event.edit("❌ **Error:** Reply to a photo/GIF/sticker.")
        
        reply = await event.get_reply_message()
        pack_arg = event.pattern_match.group(1)
        emoji = event.pattern_match.group(2) or "⚡"
        pack_name_raw = pack_arg.strip() if pack_arg else "EmpirePack"
        
        status = await event.edit(f"⚡ **Processing...**")
        
        try:
            # Media download
            media_bytes = await client.download_media(reply, bytes)
            if not media_bytes:
                return await status.edit("❌ **Error:** Could not download media.")
                
            sticker_io = prepare_sticker(media_bytes)
            if not sticker_io:
                return await status.edit("❌ **Error:** Could not process image.")

            sticker_io.name = "sticker.png"
            sent_msg = await client.send_file('me', sticker_io, force_document=True)
            raw_doc = sent_msg.media.document
            sticker_item = types.InputStickerSetItem(
                document=types.InputDocument(
                    id=raw_doc.id, access_hash=raw_doc.access_hash, file_reference=raw_doc.file_reference
                ), 
                emoji=emoji
            )

            me = await client.get_me()
            username = me.username or f"user{me.id}"
            short_name = await get_pack_short_name(me.id, pack_name_raw)
            constructed_short_name = f"{pack_name_raw.replace(' ', '_')}_{me.id}_by_{username}"
            
            try:
                if not short_name:
                    await status.edit(f"✨ **Creating Pack:** `{pack_name_raw}`...")
                    await client(functions.stickers.CreateStickerSetRequest(
                        user_id=me.id, title=pack_name_raw, short_name=constructed_short_name, stickers=[sticker_item]
                    ))
                    await save_user_pack(me.id, pack_name_raw, constructed_short_name)
                    await status.edit(f"✅ **Pack Created!**\n🔗 https://t.me/addstickers/{constructed_short_name}")
                else:
                    await status.edit(f"🚀 **Adding to `{pack_name_raw}`...**")
                    await client(functions.stickers.AddStickerToSetRequest(
                        stickerset=types.InputStickerSetShortName(short_name=short_name),
                        sticker=sticker_item
                    ))
                    await status.edit(f"✅ **Sticker Added!**\n🔗 https://t.me/addstickers/{short_name}")
            
            except Exception as e:
                # SYNC LOGIC
                if "SHORTNAME_OCCUPIED" in str(e) or "STICKERSET_INVALID" in str(e):
                    await status.edit(f"🔄 **Syncing & Adding...**")
                    await client(functions.stickers.AddStickerToSetRequest(
                        stickerset=types.InputStickerSetShortName(short_name=constructed_short_name),
                        sticker=sticker_item
                    ))
                    await save_user_pack(me.id, pack_name_raw, constructed_short_name)
                    await status.edit(f"✅ **Synced!**\n🔗 https://t.me/addstickers/{constructed_short_name}")
                else:
                    raise e

            await sent_msg.delete()
        except Exception as e:
            log.error(f"Kang Error: {e}")
            await status.edit(f"❌ **Error:** `{str(e)}` ")

    # --- 2. DELETE STICKER (.delsticker) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delsticker$'))
    async def remove_sticker_handler(event):
        if not event.is_reply:
            return await event.edit("❌ **Usage:** Reply to the sticker you want to remove.")
        
        reply = await event.get_reply_message()
        if not (reply.media and hasattr(reply.media, 'document')):
            return await event.edit("❌ **Error:** Reply to a sticker.")
        
        status = await event.edit("🗑️ **Removing from Pack...**")
        
        try:
            doc = reply.media.document
            await client(functions.stickers.RemoveStickerFromSetRequest(
                sticker=types.InputDocument(
                    id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference
                )
            ))
            await status.edit("✅ **Sticker Removed Successfully!**")
        except errors.rpcerrorlist.StickersetNotModifiedError:
            await status.edit("⚠️ **Sticker already removed or not part of your packs.**")
        except Exception as e:
            await status.edit(f"❌ **Failed:** `{str(e)}` ")

    # --- 3. DELETE FULL PACK (.delpack [packname]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delpack(?:\s+(.*))?'))
    async def delete_full_pack_handler(event):
        args = event.pattern_match.group(1)
        if not args:
            return await event.edit("❌ **Usage:** `.delpack PackName` ")
        
        pack_name = args.strip()
        status = await event.edit(f"⚠️ **Deleting full pack `{pack_name}`...**")
        
        try:
            me = await client.get_me()
            username = me.username or f"user{me.id}"
            short_name = await get_pack_short_name(me.id, pack_name)
            
            if not short_name:
                # Fallback if DB missing
                short_name = f"{pack_name.replace(' ', '_')}_{me.id}_by_{username}"

            # API to DELETE the sticker set permanently from Telegram
            await client(functions.stickers.DeleteStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=short_name)
            ))
            
            # DB Cleanup
            from database import db
            if db is not None:
                await db["sticker_packs"].delete_one({"user_id": me.id, "pack_name": pack_name.lower()})
            
            await status.edit(f"🗑️ **Pack `{pack_name}` deleted successfully.**")
        except Exception as e:
            await status.edit(f"❌ **Failed:** `{str(e)}` ")

    # --- 4. MEMIFY COMMAND ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.mm(?:\s+(.*))?'))
    async def memify_handler(event):
        if not event.is_reply:
            return await event.edit("❌ **Usage:** Reply to media.")
        text = event.pattern_match.group(1)
        if not text or ";" not in text:
            return await event.edit("❌ **Usage:** `.mm TOP ; BOTTOM` ")
        top, bottom = (text.split(";") + [""])[:2]
        status = await event.edit("🎨 **Memifying...**")
        reply = await event.get_reply_message()
        img_data = await client.download_media(reply, bytes)
        try:
            image = Image.open(io.BytesIO(img_data)).convert("RGBA")
            meme_img = draw_text(image, top.strip().upper(), bottom.strip().upper())
            output = io.BytesIO()
            meme_img.save(output, format="WEBP")
            output.seek(0)
            await client.send_file(event.chat_id, output, reply_to=reply.id)
            await status.delete()
        except Exception as e:
            await status.edit(f"❌ **Memify Error:** `{str(e)}` ")

    # --- 5. PACK LINK (.pack [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.pack(?:\s+(.*))?'))
    async def pack_handler(event):
        args = event.pattern_match.group(1)
        pack_name = args.strip() if args else "EmpirePack"
        me = await client.get_me()
        username = me.username or f"user{me.id}"
        short_name = await get_pack_short_name(me.id, pack_name)
        if not short_name:
            short_name = f"{pack_name.replace(' ', '_')}_{me.id}_by_{username}"
        await event.edit(f"📦 **Pack:** `{pack_name}`\n🔗 https://t.me/addstickers/{short_name}")
