import importlib
import logging

log = logging.getLogger(__name__)

async def load_all_modules(client):
    modules_to_load = [
        "modules.games.wordly.wordly",
        "modules.games.wordseek.wordseek",
        "modules.games.wordchain.wordchain",
        "modules.games.octopus.octopus",
        "modules.fun.clone",
        # --- Management Modules ---
        "modules.management.group_tools",
        "modules.management.info_tools"
    ]
    
    for module_path in modules_to_load:
        try:
            module = importlib.import_module(module_path)
            module.register(client)
            log.info(f"Successfully registered: {module_path}")
        except Exception as e:
            log.error(f"Failed to load module {module_path}: {e}")
