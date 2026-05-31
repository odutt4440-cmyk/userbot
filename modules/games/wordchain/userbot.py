# userbot.py
# TELETHON WORDCHAIN USERBOT
# pip install telethon

import asyncio
import random
import re
from collections import defaultdict

from telethon import TelegramClient, events
from telethon.tl.functions.messages import (
    DeleteMessagesRequest,
    SetTypingRequest
)
from telethon.tl.types import SendMessageTypingAction

# ==================================================
# CONFIG
# ==================================================

API_ID = 27309741
API_HASH = "YOUR_API_HASH"

SESSION = "userbot"

DICT_FILE = "dictionary.txt"

# typing delay
MIN_DELAY = 4
MAX_DELAY = 8

# delete saved commands automatically
DELETE_SAVED_COMMANDS = True

# ==================================================
# CLIENT
# ==================================================

client = TelegramClient(SESSION, API_ID, API_HASH)

# ==================================================
# GLOBALS
# ==================================================

WORDS = set()

STARTS = defaultdict(list)

ACTIVE_GAMES = {}
AUTOPLAY = {}

# spam modes:
# fixed letter => "x"
# random spam => "random"
SPAM_MODE = {}

ME = None

# ==================================================
# LOAD DICTIONARY
# ==================================================

def load_dictionary():

    global WORDS

    with open(DICT_FILE, "r", encoding="utf-8", errors="ignore") as f:

        for line in f:

            w = line.strip().lower()

            if not w.isalpha():
                continue

            WORDS.add(w)

            STARTS[w[0]].append(w)

    print(f"[✓] Dictionary loaded: {len(WORDS)} words")


# ==================================================
# HELPERS
# ==================================================

async def typing(chat_id):

    delay = random.uniform(MIN_DELAY, MAX_DELAY)

    try:

        await client(
            SetTypingRequest(
                peer=chat_id,
                action=SendMessageTypingAction()
            )
        )

    except:
        pass

    await asyncio.sleep(delay)


async def sm(text):
    return await client.send_message("me", text)


async def delete_saved(msg):

    if not DELETE_SAVED_COMMANDS:
        return

    try:
        await msg.delete()
    except:
        pass


def format_word(word):

    if not word:
        return word

    return word[0].upper() + word[1:]


def get_random_spam_letter():

    letters = list("abcdefghijklmnopqrstuvwxyz")

    return random.choice(letters)


def get_valid_word(
    start=None,
    end=None,
    required=None,
    banned=None,
    used=None,
    min_len=1
):

    if used is None:
        used = set()

    banned = banned or []

    if start:
        pool = STARTS.get(start.lower(), [])
    else:
        pool = list(WORDS)

    # =========================================
    # RANDOM SPAM MODE
    # =========================================

    if end == "random":
        end = get_random_spam_letter()

    # =========================================
    # PERFECT MATCH
    # =========================================

    perfect = []

    for w in pool:

        if w in used:
            continue

        if len(w) < min_len:
            continue

        if end and not w.endswith(end):
            continue

        if required and required not in w:
            continue

        bad = False

        for b in banned:

            if b in w:
                bad = True
                break

        if bad:
            continue

        perfect.append(w)

    if perfect:
        return random.choice(perfect)

    # =========================================
    # FALLBACK WITHOUT SPAM ENDING
    # =========================================

    fallback_no_end = []

    for w in pool:

        if w in used:
            continue

        if len(w) < min_len:
            continue

        if required and required not in w:
            continue

        bad = False

        for b in banned:

            if b in w:
                bad = True
                break

        if bad:
            continue

        fallback_no_end.append(w)

    if fallback_no_end:
        return random.choice(fallback_no_end)

    # =========================================
    # START LETTER ONLY
    # =========================================

    fallback_start = []

    for w in pool:

        if w in used:
            continue

        if len(w) < min_len:
            continue

        fallback_start.append(w)

    if fallback_start:
        return random.choice(fallback_start)

    return None


# ==================================================
# DELETE GROUP MESSAGE
# ==================================================

async def delete_group_message(chat_id, msg_id):

    try:

        await client(
            DeleteMessagesRequest(
                chat_id,
                [msg_id],
                revoke=True
            )
        )

    except:
        pass


# ==================================================
# GAME DETECTION
# ==================================================

GAME_PATTERNS = [
    "/startclassic",
    "/startchaos",
    "/starthard",
    "/startelim",
    "/startmelim",
    "/startrfl",
    "/startrl",
    "/startbl",
    "the first word is",
    "turn order"
]


@client.on(events.NewMessage)
async def detect_games(event):

    if event.is_private:
        return

    text = (event.raw_text or "").lower()

    found = False

    for g in GAME_PATTERNS:

        if g in text:
            found = True
            break

    if not found:
        return

    if event.chat_id not in ACTIVE_GAMES:

        ACTIVE_GAMES[event.chat_id] = {
            "used": set(),
            "title": getattr(event.chat, "title", "Unknown")
        }

        game_no = len(ACTIVE_GAMES)

        title = getattr(event.chat, "title", "Unknown")

        await sm(
            f"🎮 GAME DETECTED\n\n"
            f"GROUP: {title}\n"
            f"ID: {game_no}\n\n"
            f"Type:\n"
            f"on{game_no}"
        )


# ==================================================
# JOIN DETECTION
# ==================================================

@client.on(events.NewMessage)
async def detect_join(event):

    if event.is_private:
        return

    text = (event.raw_text or "").lower()

    if not ME:
        return

    myname = (ME.first_name or "").lower()

    myusername = ""

    if ME.username:
        myusername = ME.username.lower()

    joined = False

    if "joined" in text:

        if myname and myname in text:
            joined = True

        if myusername and myusername in text:
            joined = True

    if joined:

        ACTIVE_GAMES.setdefault(
            event.chat_id,
            {
                "used": set(),
                "title": getattr(event.chat, "title", "Unknown")
            }
        )

        title = getattr(event.chat, "title", "Unknown")

        await sm(
            f"⚡ YOU JOINED GAME\n\n"
            f"GROUP: {title}\n\n"
            f"Type:\n"
            f"yes"
        )


# ==================================================
# SAVED MESSAGE COMMANDS
# ==================================================

@client.on(events.NewMessage(chats="me"))
async def saved_commands(event):

    global MIN_DELAY, MAX_DELAY

    text = (event.raw_text or "").lower().strip()

    # =========================================
    # ON1 ON2 ON3
    # =========================================

    if text.startswith("on"):

        cmd = event.message

        number = text.replace("on", "").strip()

        if not number.isdigit():
            return

        number = int(number)

        if number <= 0:
            return

        games = list(ACTIVE_GAMES.keys())

        if number > len(games):

            await sm("❌ INVALID GAME ID")

            await delete_saved(cmd)

            return

        chat_id = games[number - 1]

        try:

            join_msg = await client.send_message(
                chat_id,
                "/join"
            )

            await asyncio.sleep(1)

            try:
                await delete_group_message(chat_id, join_msg.id)
            except:
                pass

            AUTOPLAY[chat_id] = True

            title = ACTIVE_GAMES[chat_id]["title"]

            await sm(
                f"✅ JOINED + AUTOPLAY ENABLED\n\n"
                f"GROUP: {title}"
            )

        except:

            await sm(
                "❌ FAILED TO JOIN\n\n"
                "Maybe joining time ended."
            )

        await delete_saved(cmd)

        return

    # =========================================
    # YES
    # =========================================

    if text == "yes":

        cmd = event.message

        if not ACTIVE_GAMES:
            return

        chat_id = list(ACTIVE_GAMES.keys())[-1]

        AUTOPLAY[chat_id] = True

        await sm("✅ AUTOPLAY ENABLED")

        await delete_saved(cmd)

        return

    # =========================================
    # AUTOPLAY
    # =========================================

    if text == "autoplay off":

        cmd = event.message

        for k in AUTOPLAY:
            AUTOPLAY[k] = False

        await sm("❌ AUTOPLAY OFF")

        await delete_saved(cmd)

        return

    if text == "autoplay on":

        cmd = event.message

        for k in ACTIVE_GAMES:
            AUTOPLAY[k] = True

        await sm("✅ AUTOPLAY ON")

        await delete_saved(cmd)

        return

    # =========================================
    # SPAM MODE
    # =========================================

    if text.startswith("spam "):

        cmd = event.message

        parts = text.split()

        if len(parts) == 2:

            mode = parts[1].lower()

            # spam random
            if mode == "random":

                for k in ACTIVE_GAMES:
                    SPAM_MODE[k] = "random"

                await sm(
                    "✅ RANDOM SPAM ENABLED\n"
                    "Bot will use random ending letters"
                )

            # fixed spam
            else:

                ending = mode[-1].lower()

                for k in ACTIVE_GAMES:
                    SPAM_MODE[k] = ending

                await sm(
                    f"✅ SPAM MODE ENABLED\n"
                    f"ENDING LETTER: {ending}"
                )

        await delete_saved(cmd)

        return

    # =========================================
    # SETTIME
    # =========================================

    if text.startswith("settime"):

        cmd = event.message

        parts = text.split()

        if len(parts) == 3:

            MIN_DELAY = int(parts[1])
            MAX_DELAY = int(parts[2])

            await sm(
                f"✅ DELAY UPDATED\n\n"
                f"MIN: {MIN_DELAY}\n"
                f"MAX: {MAX_DELAY}"
            )

        await delete_saved(cmd)

        return

    # =========================================
    # STATUS
    # =========================================

    if text == "status":

        cmd = event.message

        await sm(
            f"🤖 USERBOT ONLINE\n\n"
            f"WORDS: {len(WORDS)}\n"
            f"GAMES: {len(ACTIVE_GAMES)}\n"
            f"DELAY: {MIN_DELAY}-{MAX_DELAY}s"
        )

        await delete_saved(cmd)

        return


# ==================================================
# USED WORD TRACKER
# ==================================================

@client.on(events.NewMessage)
async def track_used_words(event):

    if event.is_private:
        return

    if event.chat_id not in ACTIVE_GAMES:
        return

    if event.chat_id not in AUTOPLAY:
        return

    if not AUTOPLAY[event.chat_id]:
        return

    text = (event.raw_text or "").lower()

    # =========================================
    # ACCEPTED WORD TRACK
    # =========================================

    accepted = re.search(
        r"([a-z]+)\s+is accepted",
        text
    )

    if accepted:

        accepted_word = accepted.group(1).lower()

        ACTIVE_GAMES[event.chat_id]["used"].add(
            accepted_word
        )

    # =========================================
    # USED WORD DETECT
    # =========================================

    used_match = re.search(
        r"([a-z]+)\s+has been used",
        text
    )

    if not used_match:
        return

    bad_word = used_match.group(1).lower()

    ACTIVE_GAMES[event.chat_id]["used"].add(
        bad_word
    )

    # =========================================
    # TURN CHECK
    # =========================================

    if not ME:
        return

    turn_match = re.search(
        r"turn:\s*([^\(\n]+)",
        text
    )

    if not turn_match:
        return

    current_turn_name = turn_match.group(1).strip().lower()

    me_names = []

    if ME.first_name:
        me_names.append(ME.first_name.lower())

    if ME.username:
        me_names.append(ME.username.lower())

    if ME.last_name:
        me_names.append(ME.last_name.lower())

    my_turn = False

    for n in me_names:

        if n and n in current_turn_name:
            my_turn = True
            break

    if not my_turn:
        return

    # =========================================
    # START LETTER
    # =========================================

    start_letter = bad_word[0]

    # =========================================
    # REQUIRED LETTER
    # =========================================

    required = None

    r = re.search(
        r"include\s+([a-z])",
        text
    )

    if r:
        required = r.group(1).lower()

    # =========================================
    # BANNED LETTERS
    # =========================================

    banned = []

    b = re.search(
        r"exclude\s+(.*?)(?:and|\.|\n)",
        text
    )

    if b:

        banned = re.findall(
            r"[a-z]",
            b.group(1)
        )

    # =========================================
    # MIN LENGTH
    # =========================================

    min_len = 1

    ml = re.search(
        r"at least\s+(\d+)",
        text
    )

    if ml:
        min_len = int(ml.group(1))

    # =========================================
    # SPAM MODE
    # =========================================

    end_letter = SPAM_MODE.get(event.chat_id)

    # =========================================
    # GET NEW WORD
    # =========================================

    word = get_valid_word(
        start=start_letter,
        end=end_letter,
        required=required,
        banned=banned,
        used=ACTIVE_GAMES[event.chat_id]["used"],
        min_len=min_len
    )

    # =========================================
    # NO VALID WORD
    # =========================================

    if not word:
        return

    ACTIVE_GAMES[event.chat_id]["used"].add(
        word
    )

    # =========================================
    # SEND NEW WORD
    # =========================================

    await typing(event.chat_id)

    await client.send_message(
        event.chat_id,
        format_word(word)
    )


# ==================================================
# GAME PLAYER
# ==================================================

@client.on(events.NewMessage)
async def game_handler(event):

    if event.is_private:
        return

    if event.chat_id not in AUTOPLAY:
        return

    if not AUTOPLAY[event.chat_id]:
        return

    text = (event.raw_text or "").lower()

    # must contain turn
    if "turn:" not in text:
        return

    if not ME:
        return

    # =========================================
    # STRICT TURN CHECK
    # =========================================

    me_names = []

    if ME.first_name:
        me_names.append(ME.first_name.lower())

    if ME.username:
        me_names.append(ME.username.lower())

    if ME.last_name:
        me_names.append(ME.last_name.lower())

    turn_match = re.search(
        r"turn:\s*([^\(\n]+)",
        text
    )

    if not turn_match:
        return

    current_turn_name = turn_match.group(1).strip().lower()

    my_turn = False

    for n in me_names:

        if n and n in current_turn_name:
            my_turn = True
            break

    if not my_turn:
        return

    if "your word must start with" not in text:
        return

    # =========================================
    # START LETTER
    # =========================================

    m = re.search(
        r"start with\s*([a-z])",
        text
    )

    if not m:
        return

    start_letter = m.group(1).lower()

    # =========================================
    # REQUIRED LETTER
    # =========================================

    required = None

    r = re.search(
        r"include\s+([a-z])",
        text
    )

    if r:
        required = r.group(1).lower()

    # =========================================
    # BANNED LETTERS
    # =========================================

    banned = []

    b = re.search(
        r"exclude\s+(.*?)(?:and|\.|\n)",
        text
    )

    if b:

        banned = re.findall(
            r"[a-z]",
            b.group(1)
        )

    # =========================================
    # MIN LETTERS
    # =========================================

    min_len = 1

    ml = re.search(
        r"at least\s+(\d+)",
        text
    )

    if ml:
        min_len = int(ml.group(1))

    # =========================================
    # SPAM MODE
    # =========================================

    end_letter = SPAM_MODE.get(event.chat_id)

    used = ACTIVE_GAMES[event.chat_id]["used"]

    # =========================================
    # GET WORD
    # =========================================

    word = get_valid_word(
        start=start_letter,
        end=end_letter,
        required=required,
        banned=banned,
        used=used,
        min_len=min_len
    )

    # no valid word
    if not word:
        return

    used.add(word)

    # typing effect
    await typing(event.chat_id)

    # send word
    await client.send_message(
        event.chat_id,
        format_word(word)
    )


# ==================================================
# MAIN
# ==================================================

async def main():

    global ME

    print("\nLoading dictionary...\n")

    load_dictionary()

    print("\nStarting userbot...\n")

    await client.start()

    ME = await client.get_me()

    print("[✓] Userbot started")
    print("[✓] Typing enabled")
    print("[✓] Auto gameplay enabled")
    print("[✓] Listening for games...\n")

    await sm(
        f"✅ USERBOT STARTED\n\n"
        f"Dictionary Loaded: {len(WORDS)}"
    )

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())