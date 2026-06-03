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
# SHARED ENGINE (Fast Loading)
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
    # --- State ---
    client.o_chat = None
    client.o_running = False
    client.o_answers = []
    client.o_guess_idx = 0
    client.o_waiting = False
    client.o_last_msg_id = 0
    client.o_last_cmd_time = 0 # Time-window tracking
    
    # Speed Config (Safe Turbo)
    client.o_min_delay = 3.1 
    client.o_max_delay = 3.6
    client.o_retry_int = 4.0

    # --- HELPERS ---
    def save_learned_word(word):
        word = word.lower().strip()
        if not word.isalpha() or len(word) <= 1: return
        learned_words[word] = learned_words.get(word, 0) + 1
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
        return [x[0] for x in results[:5]]

    async def click_button_turbo(event, keywords):
        if not event.buttons: return False
        for row in event.buttons:
            for btn in row:
                if any(k.lower() in btn.text.lower() for k in keywords):
                    # Setup phase buttons (instant click)
                    await event.click()
                    return True
        return False

    async def retry_loop(event):
        client.o_waiting = True
        while client.o_waiting and client.o_running:
            await asyncio.sleep(client.o_retry_int)
            if not client.o_waiting: break

            if client.o_guess_idx < len(client.o_answers):
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                await client.send_message(client.o_chat, answer)
            else:
                client.o_waiting = False
                # Try to skip if no more guesses
                await click_button_turbo(event, ["skip", "♻", "pass", "Next"])

    # =========================================================
    # HANDLERS
    # =========================================================
    
    @client.on(events.NewMessage(outgoing=True))
    async def octopus_cmds(event):
        text = event.raw_text.strip()
        if "/game@OctopusEN_Bot" in text:
            client.o_last_cmd_time = time.time() # Update start time
            client.o_chat = event.chat_id
            client.o_running = True
            await client.send_message("me", f"🐙 **Octopus Ready!** Target: `{event.chat_id}`")
        
        elif text.startswith(".octo delay"):
            try:
                p = text.split()
                client.o_min_delay, client.o_max_delay = float(p[2]), float(p[3])
                await event.edit(f"✅ Speed: {client.o_min_delay}-{client.o_max_delay}s")
            except: pass

    @client.on(events.NewMessage)
    async def octopus_engine(event):
        if not client.o_running or event.chat_id != client.o_chat: return
        
        sender = await event.get_sender()
        if not sender: return
        s_username = getattr(sender, "username", "") or ""
        
        if s_username.lower() != "octopusen_bot":
            # If someone types, stop current round retry
            if len(event.raw_text) > 1 and not event.raw_text.startswith('/'):
                client.o_waiting = False
            return

        text = event.raw_text
        low = text.lower()

        # 🔄 Reset round tracker if bot results arrive
        if any(x in low for x in ["got it right", "correct answer", "round:", "letters:", "passed the word"]):
            client.o_waiting = False

        # 1. SETUP PHASE (Time-Window Based: 30 seconds since /game command)
        setup_window = (time.time() - client.o_last_cmd_time) < 30
        
        if setup_window:
            if "choose a game type" in low:
                await click_button_turbo(event, ["gap", "🔠"])
                return
            if "how many rounds" in low:
                await click_button_turbo(event, ["50", "30"])
                return
            if "difficulty" in low:
                await click_button_turbo(event, ["hard", "💣"])
                return

        # 2. PUZZLE PHASE
        # capturing Q: or 🧩 board
        pattern_match = re.search(r"(?:🧩|Q:)\s*([A-Za-z](?:\s*[A-Za-z_])+)", text)
        if pattern_match and "_" in pattern_match.group(1):
            if event.id == client.o_last_msg_id: return
            client.o_last_msg_id = event.id
            
            pattern = pattern_match.group(1).strip()
            letters_match = re.search(r"(?:letters:|letter:)\s*(.+)", text, re.I)
            letters = letters_match.group(1) if letters_match else " ".join(re.findall(r"\b[A-Za-z]\b", text))

            ans = solve_puzzle(pattern, letters)
            client.o_answers = ans
            client.o_guess_idx = 0

            if ans:
                word = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                
                # First Guess Timing
                async with client.action(client.o_chat, 'typing'):
                    await asyncio.sleep(random.uniform(client.o_min_delay, client.o_max_delay))
                
                await client.send_message(client.o_chat, word)
                asyncio.create_task(retry_loop(event))
            else:
                # Instant skip if no dictionary word
                await click_button_turbo(event, ["skip", "♻", "pass", "Next"])
            return

        # 3. LEARNING
        if any(x in low for x in ["correct answer", "passed the word", "got it right"]):
            m = re.search(r"(?:→|⟶|answer:)\s*([A-Za-z]+)", text, re.I)
            if m: save_learned_word(m.group(1))

        if "game ended" in low:
            client.o_running = False
