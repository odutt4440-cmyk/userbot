# =========================================
# WORDSEEK TELETHON USERBOT
# ULTRA FAST + AUTO LOOP + SMART SOLVER
# FULL FINAL VERSION
# =========================================

import json
import random
import asyncio
import unicodedata

from collections import Counter
from telethon import TelegramClient, events

# =========================================
# TELEGRAM
# =========================================

API_ID = 27309741
API_HASH = "7c2cabcd8d3f982d6f790eef7262890f"

SESSION = "wordseek_session"

client = TelegramClient(
    SESSION,
    API_ID,
    API_HASH
)

# =========================================
# CONFIG
# =========================================

BOT_USERNAME = "wordseekbot"

ENABLED = False
ACTIVE_CHAT = None

MIN_DELAY = 0.05
MAX_DELAY = 0.15

CURRENT_MODE = 5

WORDS = []
COMMON = []

USED_WORDS = set()

LAST_GUESS = None

# LOOP SYSTEM

AUTO_LOOP = False
LOOP_COMMAND = "/new"

# =========================================
# LOAD WORDLISTS
# =========================================

with open("all-four.json", "r", encoding="utf-8") as f:
    ALL4 = json.load(f)

with open("common-four.json", "r", encoding="utf-8") as f:
    COMMON4 = json.load(f)

with open("all-five.json", "r", encoding="utf-8") as f:
    ALL5 = json.load(f)

with open("common-five.json", "r", encoding="utf-8") as f:
    COMMON5 = json.load(f)

with open("all-six.json", "r", encoding="utf-8") as f:
    ALL6 = json.load(f)

with open("common-six.json", "r", encoding="utf-8") as f:
    COMMON6 = json.load(f)

# =========================================
# BEST STARTERS
# =========================================

STARTERS = {
    4: "Care",
    5: "Slate",
    6: "Retain"
}

# =========================================
# STATES
# =========================================

GREEN = {}
YELLOW = {}
BLACK = set()

# =========================================
# RESET
# =========================================

def reset_state():

    global GREEN
    global YELLOW
    global BLACK
    global USED_WORDS
    global LAST_GUESS

    GREEN = {}
    YELLOW = {}
    BLACK = set()

    USED_WORDS = set()

    LAST_GUESS = None

# =========================================
# LOAD MODE
# =========================================

def load_mode(mode):

    global CURRENT_MODE
    global WORDS
    global COMMON

    CURRENT_MODE = mode

    if mode == 4:

        WORDS = ALL4.copy()
        COMMON = COMMON4.copy()

    elif mode == 5:

        WORDS = ALL5.copy()
        COMMON = COMMON5.copy()

    elif mode == 6:

        WORDS = ALL6.copy()
        COMMON = COMMON6.copy()

# =========================================
# CLEAN WORD
# =========================================

def clean_word(word):

    result = ""

    for ch in word:

        normalized = unicodedata.normalize(
            "NFKD",
            ch
        )

        for c in normalized:

            if c.isalpha():
                result += c.lower()

    return result

# =========================================
# PARSE FEEDBACK
# =========================================

def parse_feedback(text):

    lines = text.splitlines()

    target = None

    for line in reversed(lines):

        if (
            "🟩" in line
            or "🟨" in line
            or "🟥" in line
        ):

            target = line.strip()

            break

    if not target:
        return None

    parts = target.split()

    feedback = []
    guess = None

    for part in parts:

        if part in ["🟩", "🟨", "🟥"]:

            feedback.append(part)

        else:

            cleaned = clean_word(part)

            if cleaned:
                guess = cleaned

    if not guess:
        return None

    if len(feedback) != len(guess):
        return None

    return guess, feedback

# =========================================
# APPLY CONSTRAINTS
# =========================================

def apply_constraints(guess, feedback):

    global GREEN
    global YELLOW
    global BLACK

    confirmed = Counter()

    # GREEN

    for i, state in enumerate(feedback):

        char = guess[i]

        if state == "🟩":

            GREEN[i] = char

            confirmed[char] += 1

    # YELLOW

    for i, state in enumerate(feedback):

        char = guess[i]

        if state == "🟨":

            if char not in YELLOW:
                YELLOW[char] = set()

            YELLOW[char].add(i)

            confirmed[char] += 1

    # BLACK

    for i, state in enumerate(feedback):

        char = guess[i]

        if state == "🟥":

            if confirmed[char] == 0:

                BLACK.add(char)

# =========================================
# VALID WORD
# =========================================

def valid_word(word):

    word = word.lower()

    # GREEN

    for pos, char in GREEN.items():

        if word[pos] != char:
            return False

    # YELLOW

    for char, bad_positions in YELLOW.items():

        if char not in word:
            return False

        for pos in bad_positions:

            if word[pos] == char:
                return False

    # BLACK

    for char in BLACK:

        if (
            char in word
            and char not in YELLOW
            and char not in GREEN.values()
        ):
            return False

    return True

# =========================================
# BUILD FREQUENCY
# =========================================

def build_frequency(words):

    freq = Counter()

    for word in words:

        for char in set(word.lower()):

            freq[char] += 1

    return freq

# =========================================
# SCORE WORD
# =========================================

def score_word(word, freq):

    score = 0

    used = set()

    for char in word.lower():

        if char not in used:

            score += freq[char]

            used.add(char)

    return score

# =========================================
# NEXT GUESS
# =========================================

def get_next_guess():

    valid_common = [

        w for w in COMMON

        if (
            valid_word(w)
            and w.lower() not in USED_WORDS
        )
    ]

    valid_all = [

        w for w in WORDS

        if (
            valid_word(w)
            and w.lower() not in USED_WORDS
        )
    ]

    # FIRST MOVE

    if len(USED_WORDS) == 0:

        return STARTERS[CURRENT_MODE]

    # COMMON FIRST

    if valid_common:

        freq = build_frequency(valid_common)

        valid_common.sort(

            key=lambda w: score_word(w, freq),

            reverse=True
        )

        return valid_common[0].capitalize()

    # FALLBACK

    if valid_all:

        freq = build_frequency(valid_all)

        valid_all.sort(

            key=lambda w: score_word(w, freq),

            reverse=True
        )

        return valid_all[0].capitalize()

    return None

# =========================================
# SEND GUESS
# =========================================

async def send_guess(chat_id, word):

    USED_WORDS.add(word.lower())

    await asyncio.sleep(

        random.uniform(
            MIN_DELAY,
            MAX_DELAY
        )
    )

    async with client.action(chat_id, "typing"):

        await asyncio.sleep(
            random.uniform(
                0.05,
                0.12
            )
        )

        await client.send_message(
            chat_id,
            word
        )

    print(f"[SENT] {word}")

# =========================================
# AUTO LOOP NEW GAME
# =========================================

async def auto_new_game():

    global ACTIVE_CHAT

    await asyncio.sleep(
        random.uniform(1.2, 2.0)
    )

    if (
        ENABLED
        and AUTO_LOOP
        and ACTIVE_CHAT
    ):

        async with client.action(
            ACTIVE_CHAT,
            "typing"
        ):

            await asyncio.sleep(
                random.uniform(
                    0.3,
                    0.8
                )
            )

            await client.send_message(
                ACTIVE_CHAT,
                LOOP_COMMAND
            )

        print(f"[AUTO LOOP] {LOOP_COMMAND}")

# =========================================
# ENABLE
# =========================================

@client.on(
    events.NewMessage(
        outgoing=True,
        pattern=r"^\.ws on$"
    )
)
async def enable(event):

    global ENABLED

    ENABLED = True

    await event.edit(
        "✅ Solver Enabled"
    )

# =========================================
# DISABLE
# =========================================

@client.on(
    events.NewMessage(
        outgoing=True,
        pattern=r"^\.ws off$"
    )
)
async def disable(event):

    global ENABLED
    global ACTIVE_CHAT
    global AUTO_LOOP

    ENABLED = False

    AUTO_LOOP = False

    ACTIVE_CHAT = None

    reset_state()

    await event.edit(
        "❌ Solver Disabled"
    )

# =========================================
# DELAY COMMAND
# =========================================

@client.on(
    events.NewMessage(
        outgoing=True,
        pattern=r"^\.ws delay (\d+\.?\d*) (\d+\.?\d*)$"
    )
)
async def delay(event):

    global MIN_DELAY
    global MAX_DELAY

    MIN_DELAY = float(
        event.pattern_match.group(1)
    )

    MAX_DELAY = float(
        event.pattern_match.group(2)
    )

    await event.edit(
        f"⚡ Delay Set: {MIN_DELAY}-{MAX_DELAY}"
    )

# =========================================
# LOOP ON
# =========================================

@client.on(
    events.NewMessage(
        outgoing=True,
        pattern=r"^\.ws loop on$"
    )
)
async def loop_on(event):

    global AUTO_LOOP

    AUTO_LOOP = True

    await event.edit(
        "♻️ Auto Loop Enabled"
    )

# =========================================
# LOOP OFF
# =========================================

@client.on(
    events.NewMessage(
        outgoing=True,
        pattern=r"^\.ws loop off$"
    )
)
async def loop_off(event):

    global AUTO_LOOP

    AUTO_LOOP = False

    await event.edit(
        "❌ Auto Loop Disabled"
    )

# =========================================
# NEW GAME DETECT
# =========================================

@client.on(events.NewMessage(outgoing=True))
async def detect_new_game(event):

    global ACTIVE_CHAT
    global LOOP_COMMAND

    if not ENABLED:
        return

    text = event.raw_text.lower().strip()

    VALID_COMMANDS = [

        "/new",
        "/new4",
        "/new5",
        "/new6",

        "/new@wordseekbot",
        "/new4@wordseekbot",
        "/new5@wordseekbot",
        "/new6@wordseekbot"
    ]

    if text not in VALID_COMMANDS:
        return

    LOOP_COMMAND = text

    ACTIVE_CHAT = event.chat_id

    reset_state()

    # MODE

    if "new4" in text:

        load_mode(4)

    elif "new6" in text:

        load_mode(6)

    else:

        load_mode(5)

    print(f"[NEW GAME] {ACTIVE_CHAT}")
    print(f"[LOOP CMD] {LOOP_COMMAND}")

# =========================================
# MAIN SOLVER
# =========================================

@client.on(events.NewMessage)
async def solver(event):

    global LAST_GUESS

    if not ENABLED:
        return

    if event.chat_id != ACTIVE_CHAT:
        return

    sender = await event.get_sender()

    if not sender:
        return

    username = getattr(
        sender,
        "username",
        ""
    )

    if not username:
        return

    if username.lower() != BOT_USERNAME:
        return

    text = event.raw_text

    print("\n========== BOT ==========")
    print(text)
    print("=========================\n")

    # GAME START

    if "Game started!" in text:

        first_guess = get_next_guess()

        if first_guess:

            await send_guess(
                event.chat_id,
                first_guess
            )

        return

    # WIN

    if "Congrats!" in text:

        print("[WIN]")

        reset_state()

        asyncio.create_task(
            auto_new_game()
        )

        return

    # LOSE

    if "Game Over!" in text:

        print("[LOSE]")

        reset_state()

        asyncio.create_task(
            auto_new_game()
        )

        return

    # MODE DETECT

    if "4-letter" in text:

        load_mode(4)

    elif "5-letter" in text:

        load_mode(5)

    elif "6-letter" in text:

        load_mode(6)

    # FEEDBACK

    result = parse_feedback(text)

    if not result:
        return

    guess, feedback = result

    print("[GUESS]", guess)
    print("[FEEDBACK]", feedback)

    # DUPLICATE BLOCK

    if guess == LAST_GUESS:
        return

    LAST_GUESS = guess

    # APPLY FEEDBACK

    apply_constraints(
        guess,
        feedback
    )

    print("[GREEN]", GREEN)
    print("[YELLOW]", YELLOW)
    print("[BLACK]", BLACK)

    # NEXT WORD

    next_guess = get_next_guess()

    if not next_guess:

        print("[NO WORD FOUND]")

        return

    # SEND

    await send_guess(
        event.chat_id,
        next_guess
    )

# =========================================
# START
# =========================================

load_mode(5)

print("=================================")
print("🚀 WORDSEEK USERBOT RUNNING")
print("=================================")

client.start()

client.run_until_disconnected()