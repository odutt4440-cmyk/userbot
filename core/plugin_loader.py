import importlib
import logging

log = logging.getLogger(__name__)

# --- MODULES MAPPING ---
# --- core/plugin_loader.py update karo ---

# Modules ki Master List (Ab short names bhi support karega)
MODULE_MAP = {
    "wordly": "modules.games.wordly.wordly",
    "wordseek": "modules.games.wordseek.wordseek",
    "wordchain": "modules.games.wordchain.wordchain",
    "octopus": "modules.games.octopus.octopus",
    "clone": "modules.fun.clone",
    "afk": "modules.fun.afk",
    "tagger": "modules.management.tagger",
    # Dono support karega taaki mismatch na ho
    "info": "modules.management.info_tools",
    "info_tools": "modules.management.info_tools",
    "group_tools": "modules.management.group_tools",
    "management": "modules.management.group_tools"
}

async def load_all_modules(client, target_module=None):
    to_load = []
    
    # 1. Empire/Owner: Sab load karo
    if target_module is None or str(target_module).lower() in ["all", "all modules"]:
        to_load = list(set(MODULE_MAP.values())) # set() handles duplicates
    else:
        # 2. Standard: Specific module + Basic Tools (Always-ON)
        # Hum target_module ko lower karke map se asli path nikalenge
        target_clean = str(target_module).lower()
        main_path = MODULE_MAP.get(target_clean)
        
        if main_path:
            to_load.append(main_path)
            # Essential tools always load for Standard users too
            to_load.append(MODULE_MAP["info_tools"])
            to_load.append(MODULE_MAP["group_tools"])
        else:
            log.error(f"❌ Module '{target_module}' not found in MODULE_MAP!")
            return

    # 3. Registration
    for module_path in set(to_load): # set() taaki koi file do baar load na ho
        try:
            module = importlib.import_module(module_path)
            module.register(client)
            log.info(f"✅ Registered: {module_path}")
        except Exception as e:
            log.error(f"❌ Failed to load {module_path}: {e}")
