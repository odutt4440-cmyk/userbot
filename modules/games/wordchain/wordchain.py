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
    if WORDS: return # Already loaded
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
    # --- Per-User State (Critical for SaaS) ---
    client.wc_games = {}
    client.wc_autoplay = {}
    client.wc_spam = {}
    client.wc_me = None
    client.wc_delay_min = 4
    client.wc_delay_max = 8

    # --- HELPERS ---
    async def get_me():
        if not client.wc_me:
            client.wc_me = await client.get_me()
        return client.wc_me

    async def typing(chat_id):
        delay = random.uniform(client.wc_delay_min, client.wc_delay_max)
        try:
            await client(SetTypingRequest(peer=chat_id, action=SendMessageTypingAction()))
        except: pass
        await asyncio.sleep(delay)

    def get_valid_word(start=None, end=None, required=None, banned=None, used=None, min_len=1):
        used = used or set()
        banned = banned or []
        pool = STARTS.get(start.lower(), []) if start else list(WORDS)
        
        if end == "random": end = random.choice(list("abcdefghijklmnopqrstuvwxyz"))

        # Strategy 1: Perfect Match
        perfect = [w for w in pool if w not in used and len(w) >= min_len and (not end or w.endswith(end)) and (not required or required in w) and not any(b in w for b in banned)]
        if perfect: return random.choice(perfect)

        # Strategy 2: Fallback (No specific ending)
        fallback = [w for w in pool if w not in used and len(w) >= min_len and (not required or required in w) and not any(b in w for b in banned)]
        if fallback: return random.choice(fallback)

        # Strategy 3: Just any valid start
        any_valid = [w for w in pool if w not in used and len(w) >= min_len]
        return random.choice(any_valid) if any_valid else None

    # ==================================================
    # COMMANDS (Saved Messages)
    # ==================================================
    @client.on(events.NewMessage(chats="me"))
    async def saved_commands(event):
        text = event.raw_text.lower().strip()
        
        if text.startswith("on"):
            num = text.replace("on", "").strip()
            if not num.isdigit(): return
            games = list(client.wc_games.keys())
            if int(num) > len(games): return
            chat_id = games[int(num) - 1]
            try:
                msg = await client.send_message(chat_id, "/join")
                await asyncio.sleep(1)
                await client(DeleteMessagesRequest(chat_id, [msg.id], revoke=True))
                client.wc_autoplay[chat_id] = True
                await event.edit(f"✅ Joined + Autoplay ON for: `{client.wc_games[chat_id]['title']}`")
            except: pass

        elif text == "status":
            await event.edit(f"🤖 **WordChain Online**\nGames: {len(client.wc_games)}\nDelay: {client.wc_delay_min}-{client.wc_delay_max}s")

    # ==================================================
    # GAME & TURN DETECTION
    # ==================================================
    GAME_PATTERNS = ["/startclassic", "/startchaos", "/starthard", "/startelim", "the first word is"]

    @client.on(events.NewMessage)
    async def main_handler(event):
        if event.is_private: return
        text = (event.raw_text or "").lower()
        
        # 1. Detect New Games
        if any(p in text for p in GAME_PATTERNS):
            if event.chat_id not in client.wc_games:
                client.wc_games[event.chat_id] = {"used": set(), "title": getattr(event.chat, "title", "Group")}
                await client.send_message("me", f"🎮 **Game Detected** in `{client.wc_games[event.chat_id]['title']}`\nType `on{len(client.wc_games)}` to join.")

        # 2. Track Used Words & Detect Turn
        if event.chat_id not in client.wc_autoplay or not client.wc_autoplay[event.chat_id]: return

        # Track Accepted/Used Words
        accepted = re.search(r"([a-z]+)\s+(is accepted|has been used)", text)
        if accepted:
            client.wc_games[event.chat_id]["used"].add(accepted.group(1).lower())

        # Turn Check
        me = await get_me()
        me_names = [me.first_name.lower()]
        if me.username: me_names.append(me.username.lower())
        
        turn_match = re.search(r"turn:\s*([^\(\n]+)", text)
        if turn_match and any(n in turn_match.group(1).lower() for n in me_names):
            # It's our turn!
            start_letter = None
            if "start with" in text:
                m = re.search(r"start with\s*([a-z])", text)
                if m: start_letter = m.group(1).lower()
            elif accepted: # If someone just played, start with their last letter
                start_letter = accepted.group(1)[-1]

            if not start_letter: return

            # Extract constraints
            req = re.search(r"include\s+([a-z])", text)
            ban = re.search(r"exclude\s+(.*?)(?:and|\.|\n)", text)
            ml = re.search(r"at least\s+(\d+)", text)
            
            word = get_valid_word(
                start=start_letter,
                end=client.wc_spam.get(event.chat_id),
                required=req.group(1).lower() if req else None,
                banned=re.findall(r"[a-z]", ban.group(1)) if ban else [],
                used=client.wc_games[event.chat_id]["used"],
                min_len=int(ml.group(1)) if ml else 1
            )

            if word:
                client.wc_games[event.chat_id]["used"].add(word)
                await typing(event.chat_id)
                await client.send_message(event.chat_id, word[0].upper() + word[1:])
