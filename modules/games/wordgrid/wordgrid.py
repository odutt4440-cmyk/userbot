
import re, asyncio, gc, os
from telethon import events, Button
from .ocr_engine import extract_grid
from .solver import GridSolver

DICT_FILE = os.path.join(os.path.dirname(__file__), "wordgrid_dict.txt")
state = {"enabled": False, "target": None, "delay": 0.5}

def load_dict():
    if not os.path.exists(DICT_FILE): return set()
    with open(DICT_FILE, "r") as f: return set(line.strip().upper() for line in f)

WORDS = load_dict()

def register(client):
    @client.on(events.NewMessage(chats='me', pattern=r'\.(wgon|wgoff|wgdelay)'))
    async def admin_cmds(event):
        cmd = event.pattern_match.group(1)
        if cmd == "wgon": state["enabled"] = True; await event.edit("✅ WordGrid: ON")
        elif cmd == "wgoff": state["enabled"] = False; await event.edit("❌ WordGrid: OFF")
        elif cmd == "wgdelay": 
            state["delay"] = float(event.raw_text.split()[1])
            await event.edit(f"⚡ Delay set: {state['delay']}s")

    @client.on(events.NewMessage(outgoing=True))
    async def locker(event):
        if state["enabled"] and ("/new" in event.raw_text):
            state["target"] = event.chat_id
            await event.respond("🎯 Locked to this chat.")

    @client.on(events.NewMessage)
    async def game_handler(event):
        if not state["enabled"] or event.chat_id != state["target"]: return
        
        # Auto-Learning
        found = re.search(r'(?:ACCEPTED! - |found ")([\w]+)', event.raw_text, re.I)
        if found:
            word = found.group(1).upper()
            if word not in WORDS:
                WORDS.add(word)
                with open(DICT_FILE, "a") as f: f.write(f"\n{word}")
        
        # Grid Solving
        if event.media:
            # Clue extraction (e.g., S--- (4))
            clues = re.findall(r'([A-Z-]{3,})', event.raw_text.upper())
            path = await event.download_media()
            grid = extract_grid(path)
            
            if grid:
                solver = GridSolver(grid)
                for clue in clues:
                    pattern = f"^{clue.replace('-', '.')}$"
                    for word in WORDS:
                        if re.match(pattern, word) and solver.solve(word):
                            async with event.client.action(event.chat_id, 'typing'):
                                await asyncio.sleep(state["delay"])
                                await event.client.send_message(event.chat_id, word)
                                break
                del grid
                gc.collect()
