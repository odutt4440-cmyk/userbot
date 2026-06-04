import asyncio
import random
import re
import os
from collections import defaultdict
from telethon import events
from telethon.tl.functions.messages import DeleteMessagesRequest, SetTypingRequest
from telethon.tl.types import SendMessageTypingAction

# ==================================================
# SHARED DICTIONARY (Load once to save RAM)
# ==================================================
WORDS = set()
STARTS = defaultdict(list)
FOLDER = os.path.dirname(__file__)
DICT_FILE = os.path.join(FOLDER, "dictionary.txt")

def load_dictionary():
    if WORDS: return 
    if not os.path.exists(DICT_FILE):
        print(f"⚠️ WordChain: {DICT_FILE} not found!")
        return
    with open(DICT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip().lower()
            if w.isalpha():
                WORDS.add(w)
                STARTS[w[0]].append(w)
    print(f"[✓] WordChain Dictionary Loaded: {len(WORDS)} words")

load_dictionary()

# ==================================================
# THE MODULE REGISTER
# ==================================================
def register(client):
    # --- Per-User State (Isolated for SaaS) ---
    client.wc_active_games = {} 
    client.wc_autoplay = {}     
    client.wc_spam_mode = {}    # "random", "longest", or specific char
    client.wc_banned_ends = {}  
    client.wc_min_delay = 4
    client.wc_max_delay = 8
    client.wc_me = None
    client.wc_delete_saved = True

    # --- HELPERS ---
    async def get_me():
        if not client.wc_me:
            client.wc_me = await client.get_me()
        return client.wc_me

    async def typing(chat_id):
        delay = random.uniform(client.wc_min_delay, client.wc_max_delay)
        try:
            await client(SetTypingRequest(peer=chat_id, action=SendMessageTypingAction()))
        except: pass
        await asyncio.sleep(delay)

    def format_word(word):
        if not word: return word
        return word[0].upper() + word[1:]

    def get_valid_word(start=None, end=None, required=None, banned=None, used=None, min_len=1, banned_end=None):
        used = used or set()
        banned = banned or []
        pool = STARTS.get(start.lower(), []) if start else list(WORDS)
        
        pick_longest = (end == "longest")
        
        if end == "random":
            end = random.choice(list("abcdefghijklmnopqrstuvwxyz"))
        elif pick_longest:
            end = None # Reset end for searching longest overall

        # Helper to check constraints
        def is_perfect(w):
            if w in used or len(w) < min_len: return False
            if end and not w.endswith(end): return False
            if banned_end and w.endswith(banned_end): return False
            if required and required not in w: return False
            if any(b in w for b in banned): return False
            return True

        # Strategy 1: Candidate Gathering
        candidates = [w for w in pool if is_perfect(w)]
        
        if candidates:
            if pick_longest:
                return max(candidates, key=len)
            return random.choice(candidates)

        # Strategy 2: FALLBACK (Ignore spam ending but keep banned_end check)
        fallback = [w for w in pool if (w not in used and len(w) >= min_len and 
                   (not banned_end or not w.endswith(banned_end)) and 
                   (not required or required in w) and not any(b in w for b in banned))]
        
        if fallback:
            if pick_longest:
                return max(fallback, key=len)
            return random.choice(fallback)

        # Strategy 3: ABSOLUTE FALLBACK (No banned ending allowed)
        any_valid = [w for w in pool if w not in used and len(w) >= min_len and (not banned_end or not w.endswith(banned_end))]
        
        if any_valid:
            if pick_longest:
                return max(any_valid, key=len)
            return random.choice(any_valid)
            
        return None

    # ==================================================
    # SAVED MESSAGE COMMANDS (THE CONTROL PANEL)
    # ==================================================
    @client.on(events.NewMessage(chats="me"))
    async def saved_commands(event):
        text = (event.raw_text or "").lower().strip()

        # 🟢 Command: ON
        if text.startswith("on"):
            num = text.replace("on", "").strip()
            if not num.isdigit(): return
            num = int(num)
            chats = list(client.wc_active_games.keys())
            if num > len(chats):
                return await client.send_message("me", "❌ INVALID GAME ID")
            
            chat_id = chats[num - 1]
            try:
                join_msg = await client.send_message(chat_id, "/join")
                await asyncio.sleep(1)
                try: await client.delete_messages(chat_id, [join_msg.id])
                except: pass
                client.wc_autoplay[chat_id] = True
                await client.send_message("me", f"✅ **JOINED + AUTOPLAY ON**\nGroup: {client.wc_active_games[chat_id]['title']}")
            except: pass
            if client.wc_delete_saved: await event.delete()

        # 🚫 Command: BAN (Ending letter)
        elif text.startswith("ban "):
            letter = text.replace("ban ", "").strip().lower()
            if len(letter) == 1:
                if client.wc_active_games:
                    chat_id = list(client.wc_active_games.keys())[-1]
                    client.wc_banned_ends[chat_id] = letter
                    # Auto-Fix: Clear conflicting spam mode
                    if client.wc_spam_mode.get(chat_id) == letter:
                        client.wc_spam_mode[chat_id] = None
                    await client.send_message("me", f"🚫 **Ending Banned:** `{letter.upper()}`")
            if client.wc_delete_saved: await event.delete()

        # ⚪ Command: UNBAN
        elif text.startswith("unban "):
            letter = text.replace("unban ", "").strip().lower()
            if client.wc_active_games:
                chat_id = list(client.wc_active_games.keys())[-1]
                if client.wc_banned_ends.get(chat_id) == letter:
                    del client.wc_banned_ends[chat_id]
                    await client.send_message("me", f"✅ **Unbanned:** Ending `{letter.upper()}` is now allowed.")
                else:
                    await client.send_message("me", f"❌ `{letter.upper()}` was not banned.")
            if client.wc_delete_saved: await event.delete()

        # 🔥 Command: SPAM (Added Longest support)
        elif text.startswith("spam "):
            mode = text.replace("spam ", "").strip().lower()
            if client.wc_active_games:
                chat_id = list(client.wc_active_games.keys())[-1]
                
                # Check for Ban Conflict
                if len(mode) == 1 and client.wc_banned_ends.get(chat_id) == mode:
                    await client.send_message("me", f"❌ **Conflict:** Letter `{mode.upper()}` is currently BANNED. Unban it first.")
                    return

                client.wc_spam_mode[chat_id] = mode
                await client.send_message("me", f"✅ **SPAM MODE:** {mode.upper()}")
            if client.wc_delete_saved: await event.delete()

        # 📊 Command: STATUS
        elif text == "status":
            if client.wc_active_games:
                chat_id = list(client.wc_active_games.keys())[-1]
                banned = client.wc_banned_ends.get(chat_id, "None")
                spam = client.wc_spam_mode.get(chat_id, "None")
                await client.send_message("me", f"🤖 **WordChain Status**\nDelay: {client.wc_min_delay}-{client.wc_max_delay}s\nSpam: `{spam.upper()}`\nBanned End: `{banned.upper()}`")
            if client.wc_delete_saved: await event.delete()

        # ⏱ Command: SETTIME
        elif text.startswith("settime"):
            parts = text.split()
            if len(parts) == 3:
                client.wc_min_delay, client.wc_max_delay = int(parts[1]), int(parts[2])
                await client.send_message("me", f"✅ **DELAY:** {client.wc_min_delay}-{client.wc_max_delay}s")
            if client.wc_delete_saved: await event.delete()

    # ==================================================
    # GAME DETECTION & LOGIC (Original Intact)
    # ==================================================
    GAME_PATTERNS = ["/startclassic", "/startchaos", "/starthard", "/startelim", "/startmelim", "/startrfl", "/startrl", "/startbl", "the first word is", "turn order"]

    @client.on(events.NewMessage)
    async def game_monitor(event):
        if event.is_private: return
        text = (event.raw_text or "").lower()

        if any(p in text for p in GAME_PATTERNS):
            if event.chat_id not in client.wc_active_games:
                client.wc_active_games[event.chat_id] = {"used": set(), "title": getattr(event.chat, "title", "Unknown")}
                await client.send_message("me", f"🎮 **GAME DETECTED**\nID: {len(client.wc_active_games)}\nType `on{len(client.wc_active_games)}` to join.")

        me = await get_me()
        my_names = [me.first_name.lower()]
        if me.username: my_names.append(me.username.lower())
        if "joined" in text and any(n in text for n in my_names):
            client.wc_active_games.setdefault(event.chat_id, {"used": set(), "title": "Unknown"})
            client.wc_autoplay[event.chat_id] = True
            await client.send_message("me", f"⚡ **AUTOPLAY ACTIVE**")

        if event.chat_id not in client.wc_autoplay or not client.wc_autoplay[event.chat_id]:
            return

        word_used_match = re.search(r"([a-z]+)\s+(is accepted|has been used)", text)
        if word_used_match:
            client.wc_active_games[event.chat_id]["used"].add(word_used_match.group(1).lower())

        if "turn:" not in text: return
        turn_match = re.search(r"turn:\s*([^\(\n]+)", text)
        if not turn_match or not any(n in turn_match.group(1).lower() for n in my_names):
            return

        start_letter = None
        if "start with" in text:
            m = re.search(r"start with\s*([a-z])", text)
            if m: start_letter = m.group(1).lower()
        elif word_used_match:
            start_letter = word_used_match.group(1)[-1]

        if not start_letter: return

        req = re.search(r"include\s+([a-z])", text)
        ban_req = re.search(r"exclude\s+(.*?)(?:and|\.|\n)", text)
        ml = re.search(r"at least\s+(\d+)", text)
        
        word = get_valid_word(
            start=start_letter,
            end=client.wc_spam_mode.get(event.chat_id),
            required=req.group(1).lower() if req else None,
            banned=re.findall(r"[a-z]", ban_req.group(1)) if ban_req else [],
            used=client.wc_active_games[event.chat_id]["used"],
            min_len=int(ml.group(1)) if ml else 1,
            banned_end=client.wc_banned_ends.get(event.chat_id)
        )

        if word:
            client.wc_active_games[event.chat_id]["used"].add(word)
            await typing(event.chat_id)
            await client.send_message(event.chat_id, format_word(word))
