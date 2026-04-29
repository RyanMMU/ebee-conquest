import copy
import time
import traceback
import types
from pathlib import Path

from .events import EngineEventType


# normalize event names to engine event types or lowercase text
def eventname(event):
    # converts event names to standardized eventtype enum or string format
    # debug_event = str(event)
    if isinstance(event, EngineEventType):
        return event

    text = str(event or "").strip()
    compact = text.lower().replace("_", "").replace("-", "")
    # print(f"processing event: {compact}")
    for eventtype in EngineEventType:
        if compact in {
            eventtype.name.lower(),
            eventtype.value.lower(),
            eventtype.value.lower().replace("_", "").replace("-", ""),
        }:
            return eventtype

    return text.lower()


class ScriptAPI:
    # initialize the script api wrapper
    def __init__(self, engine, manager, scriptname):
        self.engine = engine
        self.manager = manager
        self.scriptname = scriptname

    # forward gold changes to the engine
    def addgold(self, country, amount):
        return self.engine.addgold(country, amount)

    # forward population changes to the engine
    def addpopulation(self, country, amount):
        return self.engine.addpopulation(country, amount)

    # forward war declarations to the engine
    def declarewar(self, attacker, defender):
        return self.engine.declarewar(attacker, defender)

    # return a deep copy of country data
    def getcountrydata(self, country):
        return copy.deepcopy(self.engine.getcountrydata(country))

    # subscribe this script to an engine even
    def subscribe(self, event, callback):
        return self.manager.subscribe(self.scriptname, event, callback)

    # unsubscribe this script from an engine event
    def unsubscribe(self, event, callback):
        return self.manager.unsubscribe(self.scriptname, event, callback)

    # emit an engine event with a copied payload
    def emit(self, event, payload=None):
        self.engine.emit(eventname(event), dict(payload or {}))

    # print a prefixed script log line.
    def log(self, message):
        print(f"scriptloader@EbeeEngine:~$ [{self.scriptname}] {message}", flush=True)


class ScriptManager:
    # initialize the script manager state
    def __init__(self, engine, folder="scripts", maxcrashes=3):
        self.engine = engine
        self.folder = Path(folder).resolve()
        self.maxcrashes = max(1, int(maxcrashes))
        self.scripts = {}
        self.failed = {}

    # load every script file in the scripts folder

    def loadall(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        loaded = []
        for path in sorted(self.folder.glob("*.py")):
            if path.name.startswith("_"):
                continue
            result = self.load(path)
            if result:
                loaded.append(result)
        return loaded

    # reload every known script and discover new files

    def reloadall(self):
        names = list(self.scripts)
        for name in names:
            self.reload(name)
        knownpaths = {record["path"] for record in self.scripts.values()}
        for path in sorted(self.folder.glob("*.py")):
            if path.name.startswith("_") or path.resolve() in knownpaths:
                continue
            self.load(path)
        return self.status()

    # load a single script from disk

    def load(self, target):
        path = self.scriptpath(target)
        if path is None:
            return None

        name = path.stem
        if name in self.scripts:
            self.unload(name)

        record = {
            "name": name,
            "path": path,
            "module": None,
            "api": None,
            "enabled": True,
            "crashes": 0,
            "loaded": time.time(),
            "subscriptions": [],
            "errors": [],
        }
        self.scripts[name] = record

        try:
            source = path.read_text(encoding="utf-8")
            module = self.createmodule(name, path, source)
            api = ScriptAPI(self.engine, self, name)
            module.__dict__["api"] = api
            record["module"] = module
            record["api"] = api

            hook = self.entrypoint(module, ("onload", "on_load"))
            if hook is not None:
                hook(api)

            self.failed.pop(name, None)
            print(f"[script:{name}] loaded", flush=True)
            return name
        except Exception as error:
            self.fail(name, error, "load")
            self.disable(name)
            return None

    # unload a script and run its shutdown hook

    def unload(self, name):
        record = self.scripts.get(str(name))
        if record is None:
            return False

        module = record.get("module")
        api = record.get("api")
        if module is not None and api is not None:
            hook = self.entrypoint(module, ("onunload", "on_unload"))
            if hook is not None:
                try:
                    hook(api)
                except Exception as error:
                    self.fail(record["name"], error, "unload")

        self.clear(record)
        self.scripts.pop(record["name"], None)
        return True

    # reload a script by name or path
    def reload(self, name):
        record = self.scripts.get(str(name))
        path = record["path"] if record is not None else self.scriptpath(name)
        if path is None:
            return None

        if record is not None:
            self.unload(record["name"])
        return self.load(path)

    # enable a script by reloading it


    def enable(self, name):
        return self.reload(name)


    # disable a script without unloading its record
    def disable(self, name):
        record = self.scripts.get(str(name))
        if record is None:
            return False

        record["enabled"] = False
        self.clear(record)
        print(f"[script:{record['name']}] disabled", flush=True)
        return True

    # subscribe a script callback to the event bus

    def subscribe(self, scriptname, event, callback):
        record = self.scripts.get(str(scriptname))
        if record is None or not record.get("enabled", False):
            return None
        if not callable(callback):
            raise TypeError("script event callback must be callable")

        key = eventname(event)

        def wrapper(payload, ownerscript=record["name"], realcallback=callback):
            owner = self.scripts.get(ownerscript)
            if owner is None or not owner.get("enabled", False):
                return
            try:
                realcallback(payload)
            except Exception as error:
                self.crash(ownerscript, error, f"event {eventname(key)}")

        self.engine.eventbus.subscribe(key, wrapper)
        record["subscriptions"].append(
            {
                "event": key,
                "callback": callback,
                "wrapper": wrapper,
            }
        )
        return wrapper

    # unsubscribe a script callback from the event bus

    def unsubscribe(self, scriptname, event, callback):
        record = self.scripts.get(str(scriptname))
        if record is None:
            return False

        key = eventname(event)
        removed = False
        kept = []
        for subscription in record["subscriptions"]:
            if subscription["event"] == key and (
                subscription["callback"] == callback or subscription["wrapper"] == callback
            ):
                self.engine.eventbus.unsubscribe(key, subscription["wrapper"])
                removed = True
            else:
                kept.append(subscription)
        record["subscriptions"] = kept
        return removed

    # summarize the current script state


    def status(self):
        return {
            name: {
                "path": str(record["path"]),
                "enabled": record["enabled"],
                "crashes": record["crashes"],
                "subscriptions": len(record["subscriptions"]),
                "errors": list(record["errors"][-5:]),
            }
            for name, record in sorted(self.scripts.items())
        }

    # build and execute a sandboxed script module

    def createmodule(self, name, path, source):
        module = types.ModuleType(f"ebeescript_{name}")
        module.__dict__.update(
            {
                "__builtins__": self.safebuiltins(),
                "__file__": str(path),
                "__name__": module.__name__,
                "__package__": "",
            }
        )
        code = compile(source, str(path), "exec")
        exec(code, module.__dict__, module.__dict__)
        return module

    # expose the safe builtin set available to scripts
    # exclusion some function cus this is sandboxed
    
    def safebuiltins(self):
        return {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "Exception": Exception,
            "float": float,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "print": print,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "ValueError": ValueError,
        }

    # resolve a script path inside the scripts folder

    def scriptpath(self, target):
        path = Path(target)
        if not path.suffix:
            path = self.folder / f"{target}.py"
        elif not path.is_absolute():
            path = self.folder / path

        try:
            resolved = path.resolve()
            resolved.relative_to(self.folder)
        except (OSError, ValueError):
            return None

        if not resolved.is_file() or resolved.suffix != ".py":
            return None
        return resolved

    # locate the first callable entrypoint in a module

    def entrypoint(self, module, names):
        for name in names:
            candidate = module.__dict__.get(name)
            if callable(candidate):
                return candidate
        return None

    # clear all event subscriptions for a script record


    def clear(self, record):
        for subscription in tuple(record.get("subscriptions", ())):
            self.engine.eventbus.unsubscribe(subscription["event"], subscription["wrapper"])
        record["subscriptions"] = []

    # record script failures and print the traceback
    def fail(self, name, error, context):
        message = f"{context}: {error}"
        record = self.scripts.get(str(name))
        if record is not None:
            record["errors"].append(message)
        self.failed[str(name)] = message
        print(f"[script:{name}] {message}", flush=True)
        print(traceback.format_exc(), flush=True)

    # count crashes and disable scripts that exceed the limit
    def crash(self, name, error, context):
        record = self.scripts.get(str(name))
        if record is None:
            return

        record["crashes"] += 1
        self.fail(name, error, context)
        if record["crashes"] >= self.maxcrashes:
            self.disable(name)


__all__ = ["ScriptAPI", "ScriptManager"]


# def debugdump(label="scriptloader", payload=None):
#
#     payload = {} if payload is None else payload
#     lines = [
#         f"label={label}",
#         f"payload_type={type(payload).__name__}",
#         f"payload_is_dict={isinstance(payload, dict)}",
#     ]
#
#
#     for index, line in enumerate(lines):
#         print(f"[scriptloader-debug:{index}] {line}", flush=True)
#
#
#
#     if isinstance(payload, dict):
#         for key in sorted(payload):
#             print(f"[scriptloader-debug] {key}={payload[key]}", flush=True)
#     elif isinstance(payload, (list, tuple, set)):
#         for index, item in enumerate(payload):
#             print(f"[scriptloader-debug] item{index}={item}", flush=True)
#     else:
#         print(f"[scriptloader-debug] payload={payload}", flush=True)
#
#     summary = {
#         "label": label,
#         "count": len(lines),
#         "payload_type": type(payload).__name__,
#     }
#     print(f"[scriptloader-debug] summary={summary}", flush=True)
#     return summary
