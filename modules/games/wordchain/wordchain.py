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
    client.wc_active_games = {} # {chat_id: {"used": set(), "title": str}}
    client.wc_autoplay = {}     # {chat_id: bool}
    client.wc_spam_mode = {}    # {chat_id: str} "random" or fixed char
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

    def get_valid_word(start=None, end=None, required=None, banned=None, used=None, min_len=1):
        used = used or set()
        banned = banned or []
        pool = STARTS.get(start.lower(), []) if start else list(WORDS)
        
        if end == "random":
            end = random.choice(list("abcdefghijklmnopqrstuvwxyz"))

        # Strategy 1: PERFECT MATCH (Start + End + Required - Banned)
        perfect = [w for w in pool if w not in used and len(w) >= min_len and (not end or w.endswith(end)) and (not required or required in w) and not any(b in w for b in banned)]
        if perfect: return random.choice(perfect)

        # Strategy 2: FALLBACK (No specific ending)
        fallback = [w for w in pool if w not in used and len(w) >= min_len and (not required or required in w) and not any(b in w for b in banned)]
        if fallback: return random.choice(fallback)

        # Strategy 3: START LETTER ONLY
        fallback_start = [w for w in pool if w not in used and len(w) >= min_len]
        return random.choice(fallback_start) if fallback_start else None

    # ==================================================
    # SAVED MESSAGE COMMANDS (THE CONTROL PANEL)
    # ==================================================
    @client.on(events.NewMessage(chats="me"))
    async def saved_commands(event):
        text = (event.raw_text or "").lower().strip()

        # Command: on1, on2, on3... (Activate Autoplay)
        if text.startswith("on"):
            num = text.replace("on", "").strip()
            if not num.isdigit(): return
            num = int(num)
            chats = list(client.wc_active_games.keys())
            if num > len(chats):
                await client.send_message("me", "❌ INVALID GAME ID")
                return
            
            chat_id = chats[num - 1]
            try:
                join_msg = await client.send_message(chat_id, "/join")
                await asyncio.sleep(1)
                try: await client.delete_messages(chat_id, [join_msg.id])
                except: pass
                client.wc_autoplay[chat_id] = True
                title = client.wc_active_games[chat_id]["title"]
                await client.send_message("me", f"✅ **JOINED + AUTOPLAY ENABLED**\nGroup: {title}")
            except:
                await client.send_message("me", "❌ FAILED TO JOIN")
            if client.wc_delete_saved: await event.delete()

        # Command: yes (Autoplay last detected)
        elif text == "yes":
            if not client.wc_active_games: return
            chat_id = list(client.wc_active_games.keys())[-1]
            client.wc_autoplay[chat_id] = True
            await client.send_message("me", "✅ AUTOPLAY ENABLED")
            if client.wc_delete_saved: await event.delete()

        # Command: spam random / spam x
        elif text.startswith("spam "):
            parts = text.split()
            if len(parts) == 2:
                mode = parts[1].lower()
                for k in client.wc_active_games:
                    client.wc_spam_mode[k] = "random" if mode == "random" else mode[-1]
                await client.send_message("me", f"✅ SPAM MODE: {mode.upper()}")
            if client.wc_delete_saved: await event.delete()

        # Command: settime <min> <max>
        elif text.startswith("settime"):
            parts = text.split()
            if len(parts) == 3:
                client.wc_min_delay, client.wc_max_delay = int(parts[1]), int(parts[2])
                await client.send_message("me", f"✅ DELAY UPDATED: {client.wc_min_delay}-{client.wc_max_delay}s")
            if client.wc_delete_saved: await event.delete()

        # Command: status
        elif text == "status":
            await client.send_message("me", f"🤖 **WordChain Online**\nWords: {len(WORDS)}\nActive Games: {len(client.wc_active_games)}\nDelay: {client.wc_min_delay}-{client.wc_max_delay}s")
            if client.wc_delete_saved: await event.delete()

    # ==================================================
    # GAME DETECTION (All Modes Supported)
    # ==================================================
    GAME_PATTERNS = [
        "/startclassic", "/startchaos", "/starthard", "/startelim", 
        "/startmelim", "/startrfl", "/startrl", "/startbl", 
        "the first word is", "turn order"
    ]

    @client.on(events.NewMessage)
    async def game_monitor(event):
        if event.is_private: return
        text = (event.raw_text or "").lower()

        # 1. Detect New Games in any mode
        if any(p in text for p in GAME_PATTERNS):
            if event.chat_id not in client.wc_active_games:
                client.wc_active_games[event.chat_id] = {"used": set(), "title": getattr(event.chat, "title", "Unknown")}
                game_no = len(client.wc_active_games)
                await client.send_message("me", f"🎮 **GAME DETECTED**\nGroup: {client.wc_active_games[event.chat_id]['title']}\nID: {game_no}\n\nType: `on{game_no}` to join.")

        # 2. Detect when User bot itself joins
        me = await get_me()
        my_names = [me.first_name.lower()]
        if me.username: my_names.append(me.username.lower())
        
        if "joined" in text and any(n in text for n in my_names):
            client.wc_active_games.setdefault(event.chat_id, {"used": set(), "title": getattr(event.chat, "title", "Unknown")})
            await client.send_message("me", f"⚡ **YOU JOINED GAME**\nGroup: {getattr(event.chat, 'title', 'Unknown')}\n\nType: `yes` for autoplay.")

        # ==================================================
        # AUTOMATIC GAMEPLAY
        # ==================================================
        if event.chat_id not in client.wc_autoplay or not client.wc_autoplay[event.chat_id]:
            return

        # Track Word Usage (Both accepted and already used)
        word_used_match = re.search(r"([a-z]+)\s+(is accepted|has been used)", text)
        if word_used_match:
            used_word = word_used_match.group(1).lower()
            client.wc_active_games[event.chat_id]["used"].add(used_word)

        # TURN DETECTION
        if "turn:" not in text: return
        
        turn_match = re.search(r"turn:\s*([^\(\n]+)", text)
        if not turn_match or not any(n in turn_match.group(1).lower() for n in my_names):
            return

        # EXTRACT CONSTRAINTS
        start_letter = None
        if "start with" in text:
            m = re.search(r"start with\s*([a-z])", text)
            if m: start_letter = m.group(1).lower()
        elif word_used_match:
            # If bot didn't specify start letter, use ending of the last accepted word
            start_letter = word_used_match.group(1)[-1]

        if not start_letter: return

        # Constraints extraction
        req = re.search(r"include\s+([a-z])", text)
        ban = re.search(r"exclude\s+(.*?)(?:and|\.|\n)", text)
        ml = re.search(r"at least\s+(\d+)", text)
        
        # FIND AND SEND WORD
        word = get_valid_word(
            start=start_letter,
            end=client.wc_spam_mode.get(event.chat_id),
            required=req.group(1).lower() if req else None,
            banned=re.findall(r"[a-z]", ban.group(1)) if ban else [],
            used=client.wc_active_games[event.chat_id]["used"],
            min_len=int(ml.group(1)) if ml else 1
        )

        if word:
            client.wc_active_games[event.chat_id]["used"].add(word)
            await typing(event.chat_id)
            await client.send_message(event.chat_id, format_word(word))
