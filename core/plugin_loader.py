import importlib
import logging

log = logging.getLogger(__name__)

# --- MODULES MAPPING ---
# Saare modules ke short aur full names yahan map hain
MODULE_MAP = {
    "wordly": "modules.games.wordly.wordly",
    "wordseek": "modules.games.wordseek.wordseek",
    "wordchain": "modules.games.wordchain.wordchain",
    "octopus": "modules.games.octopus.octopus",
    "clone": "modules.fun.clone",
    "afk": "modules.fun.afk",
    "stickers": "modules.fun.stickers",
    "tagger": "modules.management.tagger",
    "info": "modules.management.info_tools",
    "info_tools": "modules.management.info_tools",
    "group_tools": "modules.management.group_tools",
    "management": "modules.management.group_tools"
}

async def load_all_modules(client, target_module=None):
    """
    Universal Selective Loader: 
    Automatically handles prefixes like 'activate_', 'mod_', 'force_start_'
    """
    to_load = []
    
    # 🔥 AUTO-CLEANER: Kisi bhi prefix ko hata kar asli key nikalega
    target_clean = str(target_module).strip().lower() if target_module else None
    if target_clean:
        for prefix in ["activate_", "mod_", "force_start_", "start_ub_", "stop_"]:
            target_clean = target_clean.replace(prefix, "")

    # 1. EMPIRE MODE / OWNER
    if not target_clean or target_clean in ["all", "all modules", "all_modules"]:
        to_load = list(set(MODULE_MAP.values()))
        log.info("⚡ Empire Mode: Loading all handlers.")
    else:
        # 2. STANDARD MODE: Specific + Essentials
        main_path = MODULE_MAP.get(target_clean)
        if main_path:
            to_load.append(main_path)
            # Basic Management Tools hamesha chalu rahenge (Standard user ke liye bhi)
            to_load.append(MODULE_MAP["info_tools"])
            to_load.append(MODULE_MAP["group_tools"])
            log.info(f"🎯 Standard Mode: Loading [{target_clean}] + Essentials.")
        else:
            log.error(f"❌ Key '{target_clean}' not found in MODULE_MAP!")
            return

    # 3. Registration
    for module_path in set(to_load):
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, 'register'):
                module.register(client)
                log.info(f"✅ Registered: {module_path}")
        except Exception as e:
            log.error(f"❌ Failed to load {module_path}: {e}")
    # 3. Execution (Registering unique paths)
    for module_path in set(to_load):
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, 'register'):
                module.register(client)
                log.info(f"✅ Registered: {module_path}")
            else:
                log.warning(f"⚠️ Module {module_path} has no register() function.")
        except Exception as e:
            log.error(f"❌ Failed to load {module_path}: {e}")
