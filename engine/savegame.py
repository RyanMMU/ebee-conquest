import json
import os
import time

SAVES_DIRECTORY = "saves"
MAX_SAVE_SLOTS = 10


def ensuresavesdirectory():
    if not os.path.isdir(SAVES_DIRECTORY):
        os.makedirs(SAVES_DIRECTORY, exist_ok=True)


def getsaveslotpath(slotnumber):
    return os.path.join(SAVES_DIRECTORY, f"save_{slotnumber}.json")


def listsaveslots():
    ensuresavesdirectory()
    slots = []
    for slotnumber in range(1, MAX_SAVE_SLOTS + 1):
        slotpath = getsaveslotpath(slotnumber)
        if not os.path.isfile(slotpath):
            continue
        try:
            with open(slotpath, "r", encoding="utf-8") as filehandle:
                data = json.load(filehandle)
        except (OSError, json.JSONDecodeError):
            continue
        slots.append({
            "slot": slotnumber,
            "label": f"Game {slotnumber}",
            "playercountry": data.get("playercountry"),
            "turn": data.get("currentturnnumber"),
            "savedat": data.get("savedat"),
        })
    slots.sort(key=lambda entry: entry["slot"])
    return slots


def getnextavailableslot():
    ensuresavesdirectory()
    for slotnumber in range(1, MAX_SAVE_SLOTS + 1):
        if not os.path.isfile(getsaveslotpath(slotnumber)):
            return slotnumber
    return None


def writesaveslot(slotnumber, savedata):
    ensuresavesdirectory()
    savedata = dict(savedata)
    savedata["savedat"] = time.time()
    slotpath = getsaveslotpath(slotnumber)
    temppath = slotpath + ".tmp"
    with open(temppath, "w", encoding="utf-8") as filehandle:
        json.dump(savedata, filehandle)
    os.replace(temppath, slotpath)
    return slotpath


def readsaveslot(slotnumber):
    slotpath = getsaveslotpath(slotnumber)
    if not os.path.isfile(slotpath):
        return None
    try:
        with open(slotpath, "r", encoding="utf-8") as filehandle:
            return json.load(filehandle)
    except (OSError, json.JSONDecodeError):
        return None


def deletesaveslot(slotnumber):
    slotpath = getsaveslotpath(slotnumber)
    try:
        if os.path.isfile(slotpath):
            os.remove(slotpath)
            return True
    except OSError:
        pass
    return False


def serializeprovincemap(provincemap):
    serialized = {}
    for provinceid, province in provincemap.items():
        serialized[provinceid] = {
            "troops": int(province.get("troops", 0)),
            "ownercountry": province.get("ownercountry"),
            "controllercountry": province.get("controllercountry"),
            "country": province.get("country"),
            "countrycolor": list(province.get("countrycolor", (85, 85, 85))),
            "lasttroopactivityturn": province.get("lasttroopactivityturn", 0),
            "frontlineassignments": dict(province.get("frontlineassignments", {})) if isinstance(province.get("frontlineassignments"), dict) else {},
        }
    return serialized


def applyserializedprovincemap(serialized, provincemap):
    for provinceid, provincedata in (serialized or {}).items():
        province = provincemap.get(provinceid)
        if not province:
            continue
        province["troops"] = int(provincedata.get("troops", 0))
        province["ownercountry"] = provincedata.get("ownercountry")
        province["controllercountry"] = provincedata.get("controllercountry")
        province["country"] = provincedata.get("country")
        province["countrycolor"] = tuple(provincedata.get("countrycolor", (85, 85, 85)))
        province["lasttroopactivityturn"] = provincedata.get("lasttroopactivityturn", 0)
        frontlineassignments = provincedata.get("frontlineassignments", {})
        if isinstance(frontlineassignments, dict):
            province["frontlineassignments"] = dict(frontlineassignments)


def serializemovementorders(movementorderlist):
    serialized = []
    for order in movementorderlist:
        entry = dict(order)
        if "countrycolor" in entry and entry["countrycolor"] is not None:
            entry["countrycolor"] = list(entry["countrycolor"])
        serialized.append(entry)
    return serialized


def serializewarpairset(warpairset):
    return [list(pair) for pair in warpairset]


def deserializewarpairset(serialized):
    pairs = set()
    for pair in (serialized or []):
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            pairs.add((pair[0], pair[1]))
    return pairs


def serializewarrecordlookup(warrecordlookup):
    serialized = []
    for pair, record in warrecordlookup.items():
        entry = dict(record)
        entry["pair"] = list(pair)
        serialized.append(entry)
    return serialized


def deserializewarrecordlookup(serialized):
    lookup = {}
    for entry in (serialized or []):
        pair = entry.get("pair")
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        record = dict(entry)
        record["pair"] = (pair[0], pair[1])
        lookup[(pair[0], pair[1])] = record
    return lookup