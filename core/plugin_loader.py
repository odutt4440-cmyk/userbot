import importlib
import logging

log = logging.getLogger(__name__)

# --- MODULES MAPPING ---
# Ye list dhyan se dekh lo, yahi keys hum activator.py me use karenge
MODULE_MAP = {
    "wordly": "modules.games.wordly.wordly",
    "wordseek": "modules.games.wordseek.wordseek",
    "wordchain": "modules.games.wordchain.wordchain",
    "octopus": "modules.games.octopus.octopus",
    "clone": "modules.fun.clone",
    "group_tools": "modules.management.group_tools",
    "tagger": "modules.management.tagger",
    "afk": "modules.fun.afk",
    "info_tools": "modules.management.info_tools"
}

async def load_all_modules(client, target_module=None):
    """
    target_module: 
    - Agar 'None' ya 'All Modules' hai -> Saare load honge (Empire/Owner).
    - Agar specific key hai (e.g. 'afk') -> Sirf wahi load hoga (Standard).
    """
    
    modules_to_load = []

    # 1. Decide logic: Everything vs Selective
    if target_module is None or target_module.lower() == "all modules":
        modules_to_load = list(MODULE_MAP.values())
        log.info(f"⚡ Empire Mode: Loading all {len(modules_to_load)} modules.")
    else:
        # Sirf wahi module dhoondo jo user ne maanga hai
        path = MODULE_MAP.get(target_module.lower())
        if path:
            modules_to_load = [path]
            log.info(f"🎯 Standard Mode: Loading single module [{target_module}].")
        else:
            log.error(f"❌ Module '{target_module}' not found in MODULE_MAP!")
            return

    # 2. Registration Loop
    for module_path in modules_to_load:
        try:
            module = importlib.import_module(module_path)
            # Har userbot client par handler register karo
            module.register(client)
            log.info(f"✅ Successfully registered: {module_path}")
        except Exception as e:
            log.error(f"❌ Failed to load module {module_path}: {e}")
