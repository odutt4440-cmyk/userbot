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
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Resize logic (Exactly 512 on the longest side)
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
            # Media download aur resize
            media_bytes = await client.download_media(reply, bytes)
            sticker_io = prepare_sticker(media_bytes)
            
            # User aur Shortname info
            me = await client.get_me()
            username = me.username or f"user{me.id}"
            short_name = await get_pack_short_name(me.id, pack_name_raw)
            
            # 1. Pehle file upload karke "Document" object lena zaroori hai
            uploaded_file = await client.upload_file(sticker_io, file_name="sticker.png")
            media = await client(functions.messages.UploadMediaRequest(
                peer="me",
                media=types.InputMediaUploadedDocument(
                    file=uploaded_file,
                    mime_type="image/png",
                    attributes=[types.DocumentAttributeSticker(alt=emoji, stickerset=types.InputStickerSetEmpty())]
                )
            ))
            sticker_doc = types.InputStickerSetItem(document=media.document, emoji=emoji)
            
            if not short_name:
                # --- NAYA PACK BANANA ---
                new_short_name = f"{pack_name_raw.replace(' ', '_')}_{me.id}_by_{username}"
                await status.edit(f"✨ **Creating Pack:** `{pack_name_raw}`...")
                
                await client(functions.stickers.CreateStickerSetRequest(
                    user_id=me.id,
                    title=pack_name_raw,
                    short_name=new_short_name,
                    stickers=[sticker_doc]
                ))
                await save_user_pack(me.id, pack_name_raw, new_short_name)
                await status.edit(f"✅ **Pack Created!**\n[Open Pack](t.me/add-stickers/{new_short_name})")
            else:
                # --- PURANE PACK ME ADD KARNA ---
                await status.edit(f"🚀 **Adding to `{pack_name_raw}`...**")
                await client(functions.stickers.AddStickerToSetRequest(
                    stickerset=types.InputStickerSetShortName(short_name=short_name),
                    sticker=sticker_doc
                ))
                await status.edit(f"✅ **Sticker Added!**\n[Open Pack](t.me/add-stickers/{short_name})")

        except Exception as e:
            log.error(f"Kang Error: {e}")
            await status.edit(f"❌ **Error:** `{str(e)}` ")

    # --- 2. DELETE STICKER (.delsticker) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.delsticker$'))
    async def remove_sticker_handler(event):
        if not event.is_reply:
            return await event.edit("❌ **Usage:** Reply to the sticker you want to remove.")
        
        reply = await event.get_reply_message()
        if not reply.sticker:
            return await event.edit("❌ **Error:** That message is not a sticker.")
        
        status = await event.edit("🗑️ **Removing sticker...**")
        
        try:
            # Sticker ke attribute se uska pack info nikalna
            sticker_doc = reply.media.document
            await client(functions.stickers.RemoveStickerFromSetRequest(
                sticker=types.InputDocument(
                    id=sticker_doc.id,
                    access_hash=sticker_doc.access_hash,
                    file_reference=sticker_doc.file_reference
                )
            ))
            await status.edit("✅ **Sticker Removed Successfully!**\n_Note: It might take a few minutes to disappear from Telegram cache._")
        except Exception as e:
            await status.edit(f"❌ **Failed to remove:** `{str(e)}` ")

    # --- 3. MEMIFY COMMAND (.mm top ; bottom) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.mm(?:\s+(.*))?'))
    async def memify_handler(event):
        if not event.is_reply:
            return await event.edit("❌ **Usage:** Reply to media.\nExample: `.mm HELLO ; BYE` ")
        
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

    # --- 4. PACK LINK (.pack [name]) ---
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\.pack(?:\s+(.*))?'))
    async def pack_handler(event):
        args = event.pattern_match.group(1)
        pack_name = args.strip() if args else "EmpirePack"
        short_name = await get_pack_short_name(event.sender_id, pack_name)
        if short_name:
            await event.edit(f"📦 **Pack:** `{pack_name}`\n🔗 [Link](t.me/add-stickers/{short_name})")
        else:
            await event.edit(f"❌ Pack `{pack_name}` not in DB. Use `.kang` first.")
