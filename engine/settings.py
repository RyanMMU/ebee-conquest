import json
import os


SETTINGS_PATH = "settings.json"
ILMU_BASE_URL = "https://api.ilmu.ai/v1"
ILMU_MODEL = "ilmu-mini-v3.3"
DEMO_API_KEY = "sk-72b11bc620b04aefb85d89ece756fafa368241868c0c52fa"

DEFAULT_SETTINGS = {
    "volume": 50,
    "setup_complete": False,
    "player_name": "",
    "llm_mode": "online",
    "online_api_key": "",
    "use_demo_key": True,
    "online_base_url": ILMU_BASE_URL,
    "online_model": ILMU_MODEL,
    "ollama_base_url": "http://localhost:11434/v1",
    "ollama_model": "llama3.2",
}


def loadsettings(path=SETTINGS_PATH):
    settings = dict(DEFAULT_SETTINGS)
    try:
        with open(path, encoding="utf-8") as settingsfile:
            savedsettings = json.load(settingsfile)
        if isinstance(savedsettings, dict):
            settings.update(savedsettings)
            if (
                settings.get("use_demo_key", True)
                and settings.get("online_model") == "nemo-super"
            ):
                settings["online_model"] = ILMU_MODEL
    except (FileNotFoundError, OSError, ValueError, TypeError):
        pass
    return settings


def savesettings(settings, path=SETTINGS_PATH):
    mergedsettings = dict(DEFAULT_SETTINGS)
    if isinstance(settings, dict):
        mergedsettings.update(settings)

    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporarypath = f"{path}.tmp"
    with open(temporarypath, "w", encoding="utf-8") as settingsfile:
        json.dump(mergedsettings, settingsfile, indent=2)
        settingsfile.write("\n")
    os.replace(temporarypath, path)
    return mergedsettings


def updatesettings(updates, path=SETTINGS_PATH):
    settings = loadsettings(path)
    if isinstance(updates, dict):
        settings.update(updates)
    return savesettings(settings, path)


def resolvedonlineapikey(settings=None):
    settings = settings or loadsettings()
    if settings.get("use_demo_key", True):
        return DEMO_API_KEY
    return str(settings.get("online_api_key") or "").strip()
