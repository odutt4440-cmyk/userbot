import re
import json
import random
import asyncio
import os
from collections import Counter
from telethon import events
from telethon.tl.types import User
from wordfreq import top_n_list, zipf_frequency

# =========================================================
# SHARED DICTIONARY (Memory Efficient)
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
    # --- Per-User State (Isolating for Multi-User Same GC) ---
    client.o_chat = None
    client.o_running = False
    client.o_answers = []
    client.o_guess_idx = 0
    client.o_waiting_next_turn = False
    client.o_last_puzzle_id = 0 # Anti-collision lock
    
    client.o_min_delay = 2.6
    client.o_max_delay = 3.2
    client.o_retry_interval = 4.5
    client.o_max_guesses = 5

    # --- HELPERS ---
    def save_learned_word(word):
        word = word.lower().strip()
        if not word.isalpha() or len(word) <= 1: return
        if word not in learned_words: learned_words[word] = 1
        else: learned_words[word] += 1
        all_words.add(word)
        try:
            with open(CUSTOM_DICT_FILE, "w") as f:
                json.dump(learned_words, f, indent=2)
        except: pass

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
            
            score = learned_words.get(word, 0) * 10000
            score += int(zipf_frequency(word, "en") * 100)
            score += sum(word.count(c) for c in "etaoinshrdlu")
            score += 20 - len(word)
            results.append((word, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in results[:client.o_max_guesses]]

    async def click_button(event, keywords):
        if not event.buttons: return False
        # Anti-collision: Small random wait before clicking buttons
        await asyncio.sleep(random.uniform(0.5, 1.2))
        for row in event.buttons:
            for btn in row:
                try:
                    txt = btn.text.lower()
                    if any(key.lower() in txt for key in keywords):
                        await event.click(text=btn.text)
                        return True
                except: pass
        return False

    async def send_answer(answer):
        try:
            async with client.action(client.o_chat, "typing"):
                # Anti-collision: Staggered random delay
                jitter = random.uniform(0.1, 0.8) 
                await asyncio.sleep(random.uniform(client.o_min_delay, client.o_max_delay) + jitter)
            
            # Check if turn still valid before sending
            if client.o_waiting_next_turn or not client.o_running:
                await client.send_message(client.o_chat, answer)
        except: pass

    async def skip_round(event):
        if not event.buttons: return
        await asyncio.sleep(random.uniform(1.0, 2.0))
        for row in event.buttons:
            for btn in row:
                txt = btn.text.lower()
                if any(x in txt for x in ["skip", "♻", "pass"]):
                    try: await event.click(text=btn.text); return
                    except: pass
        try: await event.click(0)
        except: pass

    async def retry_guesses(event):
        client.o_waiting_next_turn = True
        while client.o_waiting_next_turn:
            await asyncio.sleep(client.o_retry_interval + random.uniform(0.1, 0.5))
            
            if not client.o_waiting_next_turn: return

            if client.o_guess_idx < len(client.o_answers):
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                await send_answer(answer)
            else:
                await skip_round(event)
                client.o_waiting_next_turn = False
                return

    # --- HANDLERS ---
    
    @client.on(events.NewMessage(outgoing=True))
    async def octopus_cmds(event):
        text = event.raw_text.strip()
        if text == "/game@OctopusEN_Bot":
            client.o_chat = event.chat_id
            client.o_running = True
            await client.send_message("me", f"🐙 **Octopus Target:** `{event.chat_id}`")
        
        elif text.startswith(".octo delay"):
            try:
                parts = text.split()
                client.o_min_delay, client.o_max_delay = float(parts[2]), float(parts[3])
                await event.edit(f"✅ **Octo Speed:** {client.o_min_delay}-{client.o_max_delay}s")
            except: pass

    @client.on(events.NewMessage)
    async def main_engine(event):
        if not client.o_running or event.chat_id != client.o_chat: return
        
        # Don't respond to messages from other userbots or yourself
        if event.out: 
            client.o_waiting_next_turn = False # If I sent a msg, stop retrying for this turn
            return

        sender = await event.get_sender()
        if not sender: return
        s_user = getattr(sender, "username", "") or ""
        
        # If any user (even another bot) sends a valid word, stop retrying
        if s_user.lower() != "octopusen_bot":
            # Round reset detection from user messages
            if len(event.raw_text) > 1 and not event.raw_text.startswith('/'):
                client.o_waiting_next_turn = False
            return

        text = event.raw_text
        low = text.lower()

        # Turn detection (Reset when bot sends round info)
        if any(x in low for x in ["round:", "point:", "letters:"]):
            client.o_waiting_next_turn = False

        # Menu Clicking
        if "choose a game type" in low:
            await click_button(event, ["gap", "🔠"])
            return
        if "how many rounds" in low:
            await click_button(event, ["50"])
            return
        if "difficulty" in low:
            await click_button(event, ["hard", "💣"])
            return

        # Pattern / Board Detection
        pattern_matches = re.findall(r"([A-Za-z](?:\s+[A-Za-z_])+)", text)
        pattern_line = next((m.strip() for m in pattern_matches if "_" in m), None)

        if pattern_line:
            # 🛡️ ANTI-COLLISION LOCK
            if event.id == client.o_last_puzzle_id: return
            client.o_last_puzzle_id = event.id

            letters_match = re.search(r"(?:letters:|letter:)\s*(.+)", text, re.I)
            letters_line = letters_match.group(1) if letters_match else " ".join(re.findall(r"\b[A-Za-z]\b", text))

            answers = solve_puzzle(pattern_line, letters_line)
            client.o_answers = answers
            client.o_guess_idx = 0

            if answers:
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                await send_answer(answer)
                asyncio.create_task(retry_guesses(event))
            else:
                await skip_round(event)
            return

        # Learning System
        if any(x in low for x in ["correct answer", "passed the word", "got it right"]):
            match = re.search(r"(?:→|⟶)\s*([A-Za-z]+)", text)
            if match: save_learned_word(match.group(1))

        if "game ended" in low:
            client.o_running = False
