import os
import glob
import logging
from telethon import events
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, StreamEnded
from database import set_vc_chat, get_vc_chat

log = logging.getLogger(__name__)

# state: {user_id: {"call": PyTgCalls, "chat": int, "queue": [(path, label)], "now": label|None}}
VC = {}


def register(client):

    # ---------------- helpers ----------------
    def state(user_id):
        return VC.get(user_id)

    async def get_call(user_id) -> PyTgCalls | None:
        """One PyTgCalls instance per user, reused forever."""
        if user_id in VC:
            return VC[user_id]["call"]
        try:
            call = PyTgCalls(client)
            await call.start()
        except Exception as e:
            log.error(f"VC init failed for {user_id}: {e}")
            return None

        VC[user_id] = {"call": call, "chat": None, "queue": [], "now": None}

        @call.on_update()
        async def _on_stream_end(pytgcalls, update):
            # master API: StreamEnded with .stream_type (AUDIO/VIDEO)
            if isinstance(update, StreamEnded) and update.stream_type == StreamEnded.Type.AUDIO:
                st = state(user_id)
                if st and st["queue"]:
                    await play_next(user_id)
                else:
                    if st:
                        st["now"] = None
                    log.info(f"Queue empty for {user_id}, stream ended naturally.")
        return call

    async def play_next(user_id):
        st = state(user_id)
        if not st or not st["queue"] or not st["chat"]:
            if st:
                st["now"] = None
            return
        path, label = st["queue"].pop(0)
        st["now"] = label
        try:
            await st["call"].play(st["chat"], MediaStream(path, video_flags=MediaStream.Flags.IGNORE))
            log.info(f"Now streaming: {label}")
        except Exception as e:
            log.error(f"play_next failed for '{label}': {e}")
            if os.path.exists(path):
                os.remove(path)
            await play_next(user_id)  # skip broken file, try next

    def cleanup_files(user_id):
        for f in glob.glob(f"vc_{user_id}_*"):
            try:
                os.remove(f)
            except OSError:
                pass

    # ---------------- 1. .vctarget ----------------
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vctarget(?:\s+(.+))?$'))
    async def vc_target(event):
        target = event.pattern_match.group(1)
        if not target:
            return await event.edit(
                "❌ **Usage:** `.vctarget @group_username` or `-100xxxxxxxxxx`"
            )
        try:
            entity = await client.get_entity(target.strip())
            await set_vc_chat(event.sender_id, entity.id)
            st = state(event.sender_id)
            if st:
                st["chat"] = entity.id
            title = getattr(entity, "title", str(entity.id))
            await event.edit(
                f"🎯 **VC Target Locked:** `{title}` (`{entity.id}`)\n\n"
                "ℹ️ Make sure:\n"
                "• Your account is in that group\n"
                "• A voice chat is already started\n\n"
                "🎙️ Now reply `.vcstream` to any audio in Saved Messages."
            )
        except Exception as e:
            await event.edit(f"❌ **Failed to resolve:** `{e}`")

    # ---------------- 2. .vcstream ----------------
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstream$'))
    async def vc_stream(event):
        reply = await event.get_reply_message()
        if not (reply and (reply.audio or reply.voice)):
            return await event.edit(
                "❌ Reply to an **audio or voice message** with `.vcstream`."
            )

        chat_id = await get_vc_chat(event.sender_id)
        if not chat_id:
            return await event.edit(
                "❌ No target set. Use `.vctarget @group` first."
            )

        status = await event.edit("⬇️ **Downloading audio...**")
        call = await get_call(event.sender_id)
        if not call:
            return await status.edit("❌ **VC engine failed to start.** Check logs.")

        st = state(event.sender_id)
        st["chat"] = chat_id

        label = reply.file.name or f"voice_{reply.id}"
        temp = f"vc_{event.sender_id}_{reply.id}.mp3"

        try:
            await client.download_media(reply, temp)

            if st["now"] is None:
                st["now"] = label
                await status.edit("📡 **Joining voice chat...**")
                await call.play(chat_id, MediaStream(temp, video_flags=MediaStream.Flags.IGNORE))
                await status.edit(
                    f"🎙️ **Streaming Live!**\n\n"
                    f"📍 **Chat:** `{chat_id}`\n"
                    f"🎶 **Now:** `{label}`\n"
                    f"📋 **Queue:** `{len(st['queue'])}`"
                )
            else:
                st["queue"].append((temp, label))
                await status.edit(
                    f"➕ **Queued:** `{label}`\n"
                    f"📋 **Queue:** `{len(st['queue'])}`"
                )
        except Exception as e:
            if os.path.exists(temp):
                os.remove(temp)
            await status.edit(f"❌ **Stream failed:** `{e}`")

    # ---------------- 3. .vcqueue ----------------
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcqueue$'))
    async def vc_queue(event):
        st = state(event.sender_id)
        if not st or (st["now"] is None and not st["queue"]):
            return await event.edit("❌ Nothing is playing right now.")
        text = f"🎶 **Now:** `{st['now']}`\n📋 **Queue:**\n"
        if st["queue"]:
            text += "\n".join(
                f"`{i}.` {label}" for i, (_, label) in enumerate(st["queue"], 1)
            )
        else:
            text += "`(empty)`"
        await event.edit(text)

    # ---------------- 4. .vcskip ----------------
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcskip$'))
    async def vc_skip(event):
        st = state(event.sender_id)
        if not st or st["now"] is None:
            return await event.edit("❌ Nothing is playing right now.")

        if st["queue"]:
            await event.edit("⏭️ **Skipping to next track...**")
            await play_next(event.sender_id)
        else:
            # Queue empty -> stay in VC, just inform
            await event.edit(
                "⚠️ **Queue is empty.** Current track will keep playing. "
                "Queue more with `.vcstream` or stop with `.vcstop`."
            )

    # ---------------- 5. .vcstop ----------------
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vcstop$'))
    async def vc_stop(event):
        st = state(event.sender_id)
        if not st:
            return await event.edit("❌ No active VC session found.")

        try:
            if st["chat"]:
                await st["call"].leave_call(st["chat"])
        except Exception as e:
            log.warning(f"leave_call: {e}")

        cleanup_files(event.sender_id)
        VC.pop(event.sender_id, None)
        await event.edit(
            "🛑 **Stream stopped.**\n"
            "Left voice chat • Queue cleared • Cache cleaned."
        )

    # ---------------- 6. .vchelp ----------------
    @client.on(events.NewMessage(chats='me', pattern=r'^\.vchelp$'))
    async def vc_help(event):
        await event.edit(
            "🎧 **VC Stream — Commands** (Saved Messages only)\n\n"
            "🎯 `.vctarget @group` — Lock target group/chat for streaming\n"
            "🎙️ `.vcstream` — Reply to audio/voice: play it in the VC (queues if busy)\n"
            "📋 `.vcqueue` — Show current track and queue\n"
            "⏭️ `.vcskip` — Skip to next queued track\n"
            "🛑 `.vcstop` — Stop stream, leave VC, clear queue & cache\n"
            "❓ `.vchelp` — Show this help\n\n"
            "**Flow:** `.vctarget @group` → reply audio `.vcstream` → enjoy → `.vcstop`"
        )
