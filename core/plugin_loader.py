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
    "tagger": "modules.management.tagger",
    "info": "modules.management.info_tools",
    "info_tools": "modules.management.info_tools",
    "group_tools": "modules.management.group_tools",
    "management": "modules.management.group_tools"
}

async def load_all_modules(client, target_module=None):
    """
    Railway Optimized Selective Loader
    """
    to_load = []
    
    # Clean the target name (remove spaces and lowercase it)
    target_clean = str(target_module).strip().lower() if target_module else None

    # 1. EMPIRE / OWNER: Load everything
    if not target_clean or target_clean in ["all", "all modules", "all_modules"]:
        to_load = list(set(MODULE_MAP.values()))
        log.info("⚡ Empire Mode: Registering all handlers.")
    else:
        # 2. STANDARD: Specific Module + Essential Tools
        main_path = MODULE_MAP.get(target_clean)
        
        if main_path:
            to_load.append(main_path)
            # Essential tools are ALWAYS loaded (Info & Group tools)
            to_load.append(MODULE_MAP["info_tools"])
            to_load.append(MODULE_MAP["group_tools"])
            log.info(f"🎯 Standard Mode: Registering [{target_clean}] + Essentials.")
        else:
            # Ye line humein batayegi ki problem kya hai
            log.error(f"❌ ERROR: Key '{target_clean}' not found in MODULE_MAP!")
            log.error(f"Available keys are: {list(MODULE_MAP.keys())}")
            return

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
