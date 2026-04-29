import copy
import time
import traceback
import types
from pathlib import Path

from .events import EngineEventType


def eventname(event):
    if isinstance(event, EngineEventType):
        return event

    text = str(event or "").strip()
    compact = text.lower().replace("_", "").replace("-", "")
    for eventtype in EngineEventType:
        if compact in {
            eventtype.name.lower(),
            eventtype.value.lower(),
            eventtype.value.lower().replace("_", "").replace("-", ""),
        }:
            return eventtype

    return text.lower()


class ScriptUIManager:
    def __init__(self, manager):
        self.manager = manager
        self.elements = {}
        self.order = []
        self.drawcallbacks = {}
        self.messages = []
        self.lastsize = (1, 1)

    def registerpanel(
        self,
        scriptname,
        uiid,
        x,
        y,
        width,
        height,
        title="",
        anchor="topleft",
        visible=True,
    ):
        return self.registerelement(
            scriptname,
            uiid,
            {
                "type": "panel",
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "title": str(title or ""),
                "anchor": anchor,
                "visible": bool(visible),
            },
        )

    def registerbutton(
        self,
        scriptname,
        uiid,
        x,
        y,
        width,
        height,
        label,
        callback=None,
        anchor="topleft",
        visible=True,
        parent=None,
    ):
        return self.registerelement(
            scriptname,
            uiid,
            {
                "type": "button",
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "label": str(label or ""),
                "callback": callback,
                "anchor": anchor,
                "visible": bool(visible),
                "parent": str(parent) if parent else None,
            },
        )

    def registerdrawcallback(self, scriptname, uiid, callback):
        if not callable(callback):
            raise TypeError("script ui draw callback must be callable")

        fullid = self.fullid(scriptname, uiid)
        self.drawcallbacks[fullid] = {
            "script": str(scriptname),
            "id": str(uiid),
            "callback": callback,
        }
        return str(uiid)

    def registerclickcallback(self, scriptname, uiid, callback):
        if not callable(callback):
            raise TypeError("script ui click callback must be callable")

        fullid = self.fullid(scriptname, uiid)
        element = self.elements.get(fullid)
        if element is None:
            raise KeyError(f"unknown script ui id: {uiid}")
        element["callback"] = callback
        return str(uiid)

    def unregister(self, scriptname, uiid=None):
        if uiid is None:
            self.clear_script(scriptname)
            return True

        fullid = self.fullid(scriptname, uiid)
        removed = False
        if fullid in self.elements:
            self.elements.pop(fullid, None)
            removed = True
        if fullid in self.drawcallbacks:
            self.drawcallbacks.pop(fullid, None)
            removed = True
        self.order = [entryid for entryid in self.order if entryid != fullid]
        return removed

    def clear_script(self, scriptname):
        prefix = f"{scriptname}:"
        for fullid in list(self.elements):
            if fullid.startswith(prefix):
                self.elements.pop(fullid, None)
        for fullid in list(self.drawcallbacks):
            if fullid.startswith(prefix):
                self.drawcallbacks.pop(fullid, None)
        self.order = [fullid for fullid in self.order if not fullid.startswith(prefix)]

    def show_message(self, text, seconds=3.0):
        message = str(text or "").strip()
        if not message:
            return
        self.messages.append(
            {
                "text": message,
                "until": time.time() + max(0.5, float(seconds or 3.0)),
            }
        )
        self.messages = self.messages[-5:]

    def handleevent(self, event):
        try:
            import pygame
        except ImportError:
            return False

        if event.type != pygame.MOUSEBUTTONDOWN or getattr(event, "button", None) != 1:
            return False

        position = getattr(event, "pos", None)
        if position is None:
            return False

        consumed = False
        for fullid in reversed(self.order):
            element = self.elements.get(fullid)
            if not element or not self.isvisible(element):
                continue

            rect = self.rectfor(element, event)
            if not rect.collidepoint(position):
                continue

            consumed = True
            if element.get("type") == "button":
                callback = element.get("callback")
                if callable(callback):
                    payload = {
                        "id": element["id"],
                        "label": element.get("label", ""),
                        "x": int(position[0]),
                        "y": int(position[1]),
                    }
                    self.manager.callscript(element["script"], callback, payload, f"ui click {element['id']}")
            break

        return consumed

    def draw(self, surface):
        try:
            import pygame
        except ImportError:
            return

        self.lastsize = surface.get_size()
        self.rundrawcallbacks(surface)

        font = pygame.font.SysFont("Arial", 14)
        titlefont = pygame.font.SysFont("Arial", 15, bold=True)
        mouseposition = pygame.mouse.get_pos()

        for fullid in list(self.order):
            element = self.elements.get(fullid)
            if not element or not self.isvisible(element):
                continue

            rect = self.rectfor(element, surface)
            if element.get("type") == "panel":
                self.drawpanel(surface, rect, element, font, titlefont)
            elif element.get("type") == "button":
                self.drawbutton(surface, rect, element, font, mouseposition)

        self.drawmessages(surface, font)

    def registerelement(self, scriptname, uiid, data):
        fullid = self.fullid(scriptname, uiid)
        data["script"] = str(scriptname)
        data["id"] = str(uiid)

        self.elements[fullid] = data
        if fullid not in self.order:
            self.order.append(fullid)
        return str(uiid)

    def rundrawcallbacks(self, surface):
        width, height = surface.get_size()
        payload = {
            "screenWidth": int(width),
            "screenHeight": int(height),
            "time": time.time(),
        }
        for record in list(self.drawcallbacks.values()):
            self.manager.callscript(
                record["script"],
                record["callback"],
                dict(payload),
                f"ui draw {record['id']}",
            )

    def drawpanel(self, surface, rect, element, font, titlefont):
        import pygame

        panelsurface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panelsurface.fill((25, 28, 34, 230))
        surface.blit(panelsurface, rect.topleft)
        pygame.draw.rect(surface, (92, 101, 112), rect, 1, border_radius=4)

        title = element.get("title", "")
        if title:
            titlesurface = titlefont.render(title, True, (235, 238, 242))
            surface.blit(titlesurface, (rect.x + 10, rect.y + 8))
            pygame.draw.line(
                surface,
                (70, 78, 88),
                (rect.x + 8, rect.y + 32),
                (rect.right - 8, rect.y + 32),
            )

    def drawbutton(self, surface, rect, element, font, mouseposition):
        import pygame

        hover = rect.collidepoint(mouseposition)
        fill = (62, 72, 84) if hover else (43, 50, 60)
        border = (130, 145, 160) if hover else (88, 100, 112)
        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, border, rect, 1, border_radius=4)

        label = str(element.get("label", ""))
        textsurface = font.render(label, True, (244, 246, 248))
        textrect = textsurface.get_rect(center=rect.center)
        if textrect.width > rect.width - 8:
            clipped = label
            while clipped and font.size(clipped + "...")[0] > rect.width - 8:
                clipped = clipped[:-1]
            textsurface = font.render((clipped + "...") if clipped else "", True, (244, 246, 248))
            textrect = textsurface.get_rect(center=rect.center)
        surface.blit(textsurface, textrect)

    def drawmessages(self, surface, font):
        import pygame

        now = time.time()
        self.messages = [message for message in self.messages if message["until"] > now]
        if not self.messages:
            return

        width, height = surface.get_size()
        y = height - 28
        for message in reversed(self.messages[-3:]):
            text = message["text"]
            while text and font.size(text)[0] > width - 40:
                text = text[:-1]
            if text != message["text"] and len(text) > 3:
                text = text[:-3] + "..."

            textsurface = font.render(text, True, (245, 245, 245))
            rect = textsurface.get_rect()
            rect.bottomright = (width - 16, y)
            background = rect.inflate(18, 10)
            pygame.draw.rect(surface, (20, 22, 26), background, border_radius=4)
            pygame.draw.rect(surface, (84, 94, 108), background, 1, border_radius=4)
            surface.blit(textsurface, rect)
            y -= background.height + 6

    def isvisible(self, element):
        if not element.get("visible", True):
            return False

        parentid = element.get("parent")
        if parentid:
            parent = self.elements.get(self.fullid(element["script"], parentid))
            if parent is not None and not self.isvisible(parent):
                return False
        return True

    def rectfor(self, element, target):
        import pygame

        width, height = self.targetsize(target)
        itemwidth = max(1, int(element.get("width", 1)))
        itemheight = max(1, int(element.get("height", 1)))
        x = int(element.get("x", 0))
        y = int(element.get("y", 0))
        anchor = str(element.get("anchor", "topleft")).lower()

        if "right" in anchor:
            left = width + x if x <= 0 else width - itemwidth - x
        elif "center" in anchor:
            left = (width - itemwidth) // 2 + x
        else:
            left = x

        if "bottom" in anchor:
            top = height + y if y <= 0 else height - itemheight - y
        elif "middle" in anchor or anchor == "center":
            top = (height - itemheight) // 2 + y
        else:
            top = y

        return pygame.Rect(left, top, itemwidth, itemheight)

    def targetsize(self, target):
        if hasattr(target, "get_size"):
            return target.get_size()

        return self.lastsize

    def fullid(self, scriptname, uiid):
        return f"{scriptname}:{uiid}"


class ScriptAPI:
    def __init__(self, engine, manager, scriptname):
        self.engine = engine
        self.manager = manager
        self.scriptname = scriptname

    def add_gold(self, country, amount):
        return self.engine.add_gold(country, amount)

    def addgold(self, country, amount):
        return self.add_gold(country, amount)

    def add_population(self, country, amount):
        return self.engine.add_population(country, amount)

    def addpopulation(self, country, amount):
        return self.add_population(country, amount)

    def add_army(self, province_id, amount):
        return self.engine.add_army(province_id, amount)

    def declare_war(self, attacker, defender):
        return self.engine.declarewar(attacker, defender)

    def declarewar(self, attacker, defender):
        return self.declare_war(attacker, defender)

    def set_province_controller(self, province_id, country):
        return self.engine.set_province_controller(province_id, country)

    def set_province_owner(self, province_id, country):
        return self.engine.set_province_owner(province_id, country)

    def get_selected_country(self):
        return self.engine.get_selected_country()

    def get_selected_province_id(self):
        return self.engine.get_selected_province_id()

    def show_script_message(self, text):
        self.manager.ui.show_message(text)
        return self.engine.show_script_message(text)

    def get_country_data(self, country):
        return copy.deepcopy(self.engine.getcountrydata(country))

    def getcountrydata(self, country):
        return self.get_country_data(country)

    def get_province_data(self, province_id):
        return copy.deepcopy(self.engine.getprovincedetails(province_id))

    def subscribe(self, event, callback):
        return self.manager.subscribe(self.scriptname, event, callback)

    def unsubscribe(self, event, callback):
        return self.manager.unsubscribe(self.scriptname, event, callback)

    def emit(self, event, payload=None):
        self.engine.emit(eventname(event), dict(payload or {}))

    def log(self, message):
        print(f"scriptloader@EbeeEngine:~$ [{self.scriptname}] {message}", flush=True)

    def register_ui_panel(
        self,
        ui_id,
        x,
        y,
        width,
        height,
        title="",
        anchor="topleft",
        visible=True,
    ):
        return self.manager.ui.registerpanel(
            self.scriptname,
            ui_id,
            x,
            y,
            width,
            height,
            title=title,
            anchor=anchor,
            visible=visible,
        )

    def register_ui_button(
        self,
        ui_id,
        x,
        y,
        width,
        height,
        label,
        callback=None,
        on_click=None,
        anchor="topleft",
        visible=True,
        parent=None,
    ):
        return self.manager.ui.registerbutton(
            self.scriptname,
            ui_id,
            x,
            y,
            width,
            height,
            label,
            callback=on_click if on_click is not None else callback,
            anchor=anchor,
            visible=visible,
            parent=parent,
        )

    def unregister_ui(self, ui_id=None):
        return self.manager.ui.unregister(self.scriptname, ui_id)

    def register_ui_draw_callback(self, ui_id, callback):
        return self.manager.ui.registerdrawcallback(self.scriptname, ui_id, callback)

    def register_ui_click_callback(self, ui_id, callback):
        return self.manager.ui.registerclickcallback(self.scriptname, ui_id, callback)


class ScriptManager:
    def __init__(self, engine, folder="scripts", maxcrashes=3):
        self.engine = engine
        self.folder = Path(folder).resolve()
        self.maxcrashes = max(1, int(maxcrashes))
        self.scripts = {}
        self.failed = {}
        self.ui = ScriptUIManager(self)

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

    def reload(self, name):
        record = self.scripts.get(str(name))
        path = record["path"] if record is not None else self.scriptpath(name)
        if path is None:
            return None

        if record is not None:
            self.unload(record["name"])
        return self.load(path)

    def enable(self, name):
        return self.reload(name)

    def disable(self, name):
        record = self.scripts.get(str(name))
        if record is None:
            return False

        record["enabled"] = False
        self.clear(record)
        print(f"[script:{record['name']}] disabled", flush=True)
        return True

    def subscribe(self, scriptname, event, callback):
        record = self.scripts.get(str(scriptname))
        if record is None or not record.get("enabled", False):
            return None
        if not callable(callback):
            raise TypeError("script event callback must be callable")

        key = eventname(event)

        def wrapper(payload, ownerscript=record["name"], realcallback=callback):
            self.callscript(ownerscript, realcallback, payload, f"event {eventname(key)}")

        self.engine.eventbus.subscribe(key, wrapper)
        record["subscriptions"].append(
            {
                "event": key,
                "callback": callback,
                "wrapper": wrapper,
            }
        )
        return wrapper

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

    def drawui(self, surface):
        self.ui.draw(surface)

    def handleuievent(self, event):
        return self.ui.handleevent(event)

    def callscript(self, scriptname, callback, payload, context):
        record = self.scripts.get(str(scriptname))
        if record is None or not record.get("enabled", False):
            return None

        try:
            return callback(payload)
        except Exception as error:
            self.crash(scriptname, error, context)
            return None

    def status(self):
        return {
            name: {
                "path": str(record["path"]),
                "enabled": record["enabled"],
                "crashes": record["crashes"],
                "subscriptions": len(record["subscriptions"]),
                "ui": sum(1 for fullid in self.ui.elements if fullid.startswith(f"{name}:")),
                "errors": list(record["errors"][-5:]),
            }
            for name, record in sorted(self.scripts.items())
        }

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
            "getattr": getattr,
            "hasattr": hasattr,
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
            "TypeError": TypeError,
            "ValueError": ValueError,
        }

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

    def entrypoint(self, module, names):
        for name in names:
            candidate = module.__dict__.get(name)
            if callable(candidate):
                return candidate
        return None

    def clear(self, record):
        for subscription in tuple(record.get("subscriptions", ())):
            self.engine.eventbus.unsubscribe(subscription["event"], subscription["wrapper"])
        record["subscriptions"] = []
        self.ui.clear_script(record["name"])

    def fail(self, name, error, context):
        message = f"{context}: {error}"
        record = self.scripts.get(str(name))
        if record is not None:
            record["errors"].append(message)
        self.failed[str(name)] = message
        print(f"[script:{name}] {message}", flush=True)
        print(traceback.format_exc(), flush=True)

    def crash(self, name, error, context):
        record = self.scripts.get(str(name))
        if record is None:
            return

        record["crashes"] += 1
        self.fail(name, error, context)
        if record["crashes"] >= self.maxcrashes:
            self.disable(name)


__all__ = ["ScriptAPI", "ScriptManager", "ScriptUIManager"]
