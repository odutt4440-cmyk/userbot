import re
import json
import random
import asyncio
import os
import time
from collections import Counter
from telethon import events
from telethon.tl.types import User
from wordfreq import top_n_list, zipf_frequency

# =========================================================
# SHARED ENGINE
# =========================================================
FOLDER = os.path.dirname(__file__)
CUSTOM_DICT_FILE = os.path.join(FOLDER, "octopus_words.json")

english_words = top_n_list("en", 120000)
all_words = set()
for w in english_words:
    w = w.lower().strip()
    if w.isalpha() and len(w) >= 3 and zipf_frequency(w, "en") > 2:
        all_words.add(w)

learned_words = {}
if os.path.exists(CUSTOM_DICT_FILE):
    try:
        with open(CUSTOM_DICT_FILE, "r") as f:
            learned_words = json.load(f)
            for w in learned_words:
                if w.isalpha(): all_words.add(w.lower().strip())
    except: pass

# =========================================================
# THE MODULE REGISTER
# =========================================================
def register(client):
    client.o_chat = None
    client.o_running = False
    client.o_answers = []
    client.o_guess_idx = 0
    client.o_waiting = False
    client.o_last_msg_id = 0
    client.o_start_msg_id = 0
    client.o_my_name = None
    
    client.o_min_delay = 3.1 
    client.o_max_delay = 3.6
    client.o_retry_int = 4.2

    def solve_puzzle(pattern_line, letters_line):
        pattern = re.sub(r"[^A-Za-z_]", "", pattern_line).lower()
        letters = re.findall(r"[A-Za-z]", letters_line)
        usable = [x.lower() for x in letters]
        for ch in pattern:
            if ch != "_": usable.append(ch)
        usable_counter = Counter(usable)
        results = []
        for word in all_words:
            if len(word) != len(pattern): continue
            if not all(p == "_" or p == w for p, w in zip(pattern, word)): continue
            wc = Counter(word)
            if any(wc[ch] > usable_counter[ch] for ch in wc): continue
            score = learned_words.get(word, 0) * 10000 + int(zipf_frequency(word, "en") * 100) + sum(word.count(c) for c in "etaoinshrdlu")
            results.append((word, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in results[:5]]

    async def setup_clicker(event, target_text, must_not_have=None):
        """Strict setup button clicker."""
        if not event.buttons: return False
        await asyncio.sleep(0.5) # Small buffer to let buttons load
        for row in event.buttons:
            for btn in row:
                t = btn.text.lower()
                if target_text.lower() in t:
                    if must_not_have and must_not_have.lower() in t:
                        continue
                    try: 
                        await event.click(text=btn.text)
                        return True
                    except: pass
        return False

    async def retry_loop(event, msg_id):
        client.o_waiting = True
        while client.o_waiting and client.o_running:
            await asyncio.sleep(client.o_retry_int)
            if not client.o_waiting or client.o_last_msg_id != msg_id: break
            if client.o_guess_idx < len(client.o_answers):
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                await client.send_message(client.o_chat, answer)
            else:
                client.o_waiting = False
                try: await event.click(text="skip")
                except: pass

    @client.on(events.NewMessage(outgoing=True))
    async def octopus_cmds(event):
        if "/game@OctopusEN_Bot" in event.raw_text:
            client.o_start_msg_id = event.id 
            client.o_chat = event.chat_id
            client.o_running = True
            if not client.o_my_name:
                me = await client.get_me()
                client.o_my_name = me.first_name
            await client.send_message("me", "🐙 **Turbo Engine Locked for Setup.**")

    @client.on(events.NewMessage)
    @client.on(events.MessageEdited)
    async def octopus_engine(event):
        if not client.o_running or event.chat_id != client.o_chat: return
        
        sender = await event.get_sender()
        if not sender: return
        s_user = (getattr(sender, "username", "") or "").lower()
        
        if s_user != "octopusen_bot":
            if not event.out and len(event.raw_text or "") > 1: client.o_waiting = False
            return

        text = event.raw_text or ""
        low = text.lower()

        if any(x in low for x in ["got it right", "correct answer", "round:", "letters:", "passed"]):
            client.o_waiting = False

        # --- 1. STRICT SETUP FLOW ---
        # Game Type: Select Gap-filling but AVOID Word Paraphrase
        if "choose a game type" in low and event.reply_to_msg_id == client.o_start_msg_id:
            await setup_clicker(event, "Gap", must_not_have="Paraphrase")
            return

        # Rounds: Select 50
        if "how many rounds" in low and (not client.o_my_name or client.o_my_name in text):
            await setup_clicker(event, "50")
            return

        # Difficulty: Select Hard
        if "difficulty" in low and (not client.o_my_name or client.o_my_name in text):
            await setup_clicker(event, "hard")
            return

        # --- 2. PUZZLE SOLVER ---
        pattern_match = re.search(r"(?:🧩|Q:)\s*([A-Za-z](?:\s*[A-Za-z_])+)", text)
        if pattern_match and "_" in pattern_match.group(1):
            if event.id == client.o_last_msg_id and "Round:" not in text: return
            client.o_last_msg_id = event.id
            
            pattern = pattern_match.group(1).strip()
            letters_match = re.search(r"(?:letters:|letter:|🔠)\s*(.+)", text, re.I)
            letters = letters_match.group(1) if letters_match else " ".join(re.findall(r"\b[A-Z]\b", text))

            ans = solve_puzzle(pattern, letters)
            client.o_answers = ans
            client.o_guess_idx = 0

            if ans:
                word = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                async with client.action(client.o_chat, 'typing'):
                    await asyncio.sleep(random.uniform(client.o_min_delay, client.o_max_delay))
                await client.send_message(client.o_chat, word)
                asyncio.create_task(retry_loop(event, event.id))
            else:
                try: await event.click(text="skip")
                except: pass
            return

        if "game ended" in low: client.o_running = False
