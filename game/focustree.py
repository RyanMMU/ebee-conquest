import datetime
import math

from dataclasses import dataclass
from typing import Any, Mapping

from .focuseffects import FocusEffectContext, FocusEffectRegistry, createeffectregistry


@dataclass(frozen=True)
class Focus:
    id: str
    title: str
    description: str = ""
    turncount: int = 1
    prerequisites: tuple[str, ...] = ()
    mutuallyexclusive: tuple[str, ...] = ()
    effects: tuple[Mapping[str, Any], ...] = ()
    icon: str = ""
    image: str = ""
    x: int = 0
    y: int = 0
    focustype: str = "administrative_focus"
    durationdays: int = 5
    politicalpowercost: int = 0
    requirements: Mapping[str, Any] | None = None
    availablecondition: Mapping[str, Any] | None = None
    bypasscondition: Mapping[str, Any] | None = None
    cancelconditions: Mapping[str, Any] | None = None
    aiweight: int = 1
    eventtrigger: str = ""
    branch: str = ""

    @classmethod
    def fromdata(cls, data: Mapping[str, Any]):
        focusid = str(data.get("id", "")).strip()
        if not focusid:
            raise ValueError("fail!! id canot be empty")

        title = str(data.get("title", focusid)).strip() or focusid
        description = str(data.get("description", "")).strip()
        durationdays = max(1, int(data.get("duration_days", data.get("days", 0)) or 0))
        if "duration_days" in data or "days" in data:
            turncount = max(1, int(math.ceil(durationdays / 5.0)))
        else:
            turncount = max(1, int(data.get("turns", data.get("turns_required", 1)) or 1))
            durationdays = turncount * 5
        prerequisites = tuple(str(item).strip() for item in data.get("prerequisites", ()) if str(item).strip())
        mutuallyexclusive = tuple(
            str(item).strip() for item in data.get("mutually_exclusive", ()) if str(item).strip()
        )
        effectdata = data.get("effects", data.get("completion_effect", ()))
        if isinstance(effectdata, Mapping):
            effectdata = (effectdata,)
        effects = tuple(dict(effect) for effect in effectdata if isinstance(effect, Mapping))
        icon = str(data.get("icon", "")).strip()
        image = str(data.get("image", "")).strip()

        position = data.get("position", {})
        if isinstance(position, Mapping):
            defaultx = position.get("x", 0)
            defaulty = position.get("y", 0)
        else:
            defaultx = 0
            defaulty = 0

        return cls(
            id=focusid,
            title=title,
            description=description,
            turncount=turncount,
            prerequisites=prerequisites,
            mutuallyexclusive=mutuallyexclusive,
            effects=effects,
            icon=icon,
            image=image,
            x=int(data.get("x", defaultx) or 0),
            y=int(data.get("y", defaulty) or 0),
            focustype=str(data.get("focus_type", data.get("type", "administrative_focus")) or "administrative_focus").strip(),
            durationdays=durationdays,
            politicalpowercost=max(0, int(data.get("political_power_cost", 0) or 0)),
            requirements=dict(data.get("requirements", {}) or {}),
            availablecondition=dict(data.get("available_condition", {}) or {}),
            bypasscondition=dict(data.get("bypass_condition", {}) or {}),
            cancelconditions=dict(data.get("cancel_conditions", {}) or {}),
            aiweight=max(0, int(data.get("ai_weight", 1) or 0)),
            eventtrigger=str(data.get("event_trigger", "") or "").strip(),
            branch=str(data.get("branch", "") or "").strip(),
        )


@dataclass(frozen=True)
class FocusStartResult:
    success: bool
    focusid: str | None = None
    reason: str = ""

# @dataclass(frozen=True)
@dataclass(frozen=True)
class FocusAdvanceResult:
    activefocusid: str | None = None
    completedfocusid: str | None = None
    turnsspent: int = 0
    turnsrequired: int = 0
    appliedeffects: tuple[Mapping[str, Any], ...] = ()
    message: str = ""


class FocusTree:
    def __init__(
        self,
        treeid: str,
        country: str | None,
        name: str,
        focuses,
        cover_image: str = "",
        effectregistry: FocusEffectRegistry | None = None,
    ):
        self.treeid = str(treeid or "focus_tree")
        self.country = country
        self.name = str(name or self.treeid)
        self.cover_image = str(cover_image or "")
        self.focuses: dict[str, Focus] = {focus.id: focus for focus in focuses}
        self.completedids: set[str] = set()
        self.failedids: set[str] = set()
        self.bypassedids: set[str] = set()
        self.activeid: str | None = None
        self.activeturns = 0.0
        self.progress: dict[str, float] = {}
        self.lastmessage = ""
        self.effectregistry = effectregistry or createeffectregistry()
        self.exclusives = self.buildexclusives()
        self.dynamiccontext: dict[str, Any] = {}
        self.validate()





#@dataclass(frozen=True)


    # create empty focus tree with no focus
    @classmethod
    def empty(cls, country: str | None = None):
        name = f"{country} National Policy" if country else "National Policy"
        return cls("empty", country, name, ())





    def buildexclusives(self):
        exclusives = {focusid: set() for focusid in self.focuses}
        for focus in self.focuses.values():
            for otherid in focus.mutuallyexclusive:
                exclusives.setdefault(focus.id, set()).add(otherid)
                exclusives.setdefault(otherid, set()).add(focus.id)
        return exclusives




    # check for prerequisite
    def validate(self):
        focusids = set(self.focuses)
        for focus in self.focuses.values():
            missingprerequisites = set(focus.prerequisites) - focusids
            if missingprerequisites:
                missing = ", ".join(sorted(missingprerequisites))
                raise ValueError(f"Focus '{focus.id}' references unknown prerequisites: {missing}")

            missingexclusive = set(focus.mutuallyexclusive) - focusids
            if missingexclusive:
                missing = ", ".join(sorted(missingexclusive))
                raise ValueError(f"Focus '{focus.id}' references unknown mutually exclusive focuses: {missing}")

    def setcontext(self, context: Mapping[str, Any] | None):
        self.dynamiccontext = dict(context or {})

    def getfocus(self, focusid: str | None):
        if focusid is None:
            return None
        return self.focuses.get(str(focusid))

    def focuscost(self, focusid: str | None):
        focus = self.getfocus(focusid)
        return focus.politicalpowercost if focus else 0

    def _contextvalue(self, key):
        return self.dynamiccontext.get(str(key))

    def _coerce_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1", "active"}
        return bool(value)

    def _compare_value(self, actual, expected):
        if isinstance(expected, (list, tuple, set)):
            return any(self._compare_value(actual, item) for item in expected)
        if isinstance(expected, bool):
            return self._coerce_bool(actual) == expected
        if isinstance(expected, (int, float)):
            try:
                return float(actual) == float(expected)
            except (TypeError, ValueError):
                return False
        return str(actual or "").strip().lower() == str(expected or "").strip().lower()

    def _compare_date(self, actual, expected, operator):
        try:
            actualdate = datetime.date.fromisoformat(str(actual)[:10])
            expecteddate = datetime.date.fromisoformat(str(expected)[:10])
        except ValueError:
            return False
        if operator == ">=":
            return actualdate >= expecteddate
        if operator == "<":
            return actualdate < expecteddate
        return actualdate == expecteddate

    def checkcondition(self, condition):
        if not condition:
            return True, ""
        if not isinstance(condition, Mapping):
            return True, ""

        allof = condition.get("all_of")
        if allof:
            for child in allof:
                passed, reason = self.checkcondition(child)
                if not passed:
                    return False, reason

        anyof = condition.get("any_of")
        if anyof:
            reasons = []
            for child in anyof:
                passed, reason = self.checkcondition(child)
                if passed:
                    break
                reasons.append(reason)
            else:
                return False, next((reason for reason in reasons if reason), "No alternate condition is met.")

        notcondition = condition.get("not")
        if notcondition:
            passed, _ = self.checkcondition(notcondition)
            if passed:
                return False, "Blocked by political situation."

        for key, expected in condition.get("min", {}).items():
            try:
                if float(self._contextvalue(key) or 0) < float(expected):
                    return False, f"Requires {key} >= {expected}."
            except (TypeError, ValueError):
                return False, f"Requires {key} >= {expected}."

        for key, expected in condition.get("max", {}).items():
            try:
                if float(self._contextvalue(key) or 0) > float(expected):
                    return False, f"Requires {key} <= {expected}."
            except (TypeError, ValueError):
                return False, f"Requires {key} <= {expected}."

        if "date_at_least" in condition and not self._compare_date(self._contextvalue("current_date"), condition["date_at_least"], ">="):
            return False, f"Requires date >= {condition['date_at_least']}."
        if "date_before" in condition and not self._compare_date(self._contextvalue("current_date"), condition["date_before"], "<"):
            return False, f"Requires date < {condition['date_before']}."

        reserved = {"all_of", "any_of", "not", "min", "max", "date_at_least", "date_before"}
        for key, expected in condition.items():
            if key in reserved:
                continue
            if key == "completed_focus":
                if str(expected) not in self.completedids:
                    return False, f"Requires completed focus: {expected}."
                continue
            if not self._compare_value(self._contextvalue(key), expected):
                return False, f"Requires {key} = {expected}."
        return True, ""


    # focus start
    def startfocus(self, focusid: str):
        focus = self.focuses.get(str(focusid or "").strip())
        if focus is None:
            return self.startresult(False, None, "Focus does not exist.")

        canstart, reason = self.canstartfocus(focus.id)
        if not canstart:
            return self.startresult(False, focus.id, reason)
        # print("start focus", focus.id)



        self.activeid = focus.id
        self.activeturns = self.progress.get(focus.id, 0.0)
        return self.startresult(True, focus.id, f"Started focus: {focus.title}")



    def advanceturn(self, context: FocusEffectContext | None = None):
        if self.activeid is None:
            return FocusAdvanceResult(message="No active focus.")


        focus = self.focuses[self.activeid]
        if focus.cancelconditions and self.checkcondition(focus.cancelconditions)[0]:
            self.failedids.add(focus.id)
            self.progress[focus.id] = self.activeturns
            self.activeid = None
            self.activeturns = 0.0
            self.lastmessage = f"{focus.title} failed because the political situation changed."
            return FocusAdvanceResult(message=self.lastmessage)

        speed = 1.0
        if context is not None:
            try:
                speed = max(0.05, float(context.metadata.get("focus_progress_multiplier", 1.0)))
            except (TypeError, ValueError):
                speed = 1.0
        self.activeturns += speed
        self.progress[focus.id] = min(self.activeturns, focus.turncount)



        if self.activeturns < focus.turncount:
            remaining = focus.turncount - self.activeturns
            self.lastmessage = f"{focus.title}: {math.ceil(remaining)} turn(s) remaining."
            return FocusAdvanceResult(
                activefocusid=focus.id,
                turnsspent=int(math.floor(self.activeturns)),
                turnsrequired=focus.turncount,
                message=self.lastmessage,
            )


        appliedeffects = ()
        if context is not None:
            appliedeffects = tuple(self.effectregistry.apply(focus.effects, context))

        self.completedids.add(focus.id)
        self.progress[focus.id] = focus.turncount
        self.activeid = None
        self.activeturns = 0.0
        self.lastmessage = f"Completed focus: {focus.title}"

        return FocusAdvanceResult(
            completedfocusid=focus.id,
            turnsspent=focus.turncount,
            turnsrequired=focus.turncount,
            appliedeffects=appliedeffects,
            message=self.lastmessage,
        )






    def canstartfocus(self, focusid: str):
        focus = self.focuses.get(focusid)
        if focus is None:
            return False, "Focus does not exist"
        if focus.id in self.completedids:
            return False, "Focus already CONMPLETED!."
        if focus.id in self.failedids:
            return False, "Focus failed and cannot be restarted."
        if focus.id in self.bypassedids:
            return False, "Focus has been bypassed."
        if self.activeid is not None:
            activefocus = self.focuses.get(self.activeid)
            activetitle = activefocus.title if activefocus else self.activeid
            return False, f"Another focus is ACTIVE: {activetitle}"

        missing = self.missingprerequisites(focus.id)
        if missing:
            return False, "MISSING prerequisites: " + ", ".join(missing)


        blocked = self.completedexclusivefocuses(focus.id)
        if blocked:
            return False, "BLOCKED by mutually exclusive focus: " + ", ".join(blocked)

        bypassed, _ = self.checkcondition(focus.bypasscondition)
        if focus.bypasscondition and bypassed:
            self.bypassedids.add(focus.id)
            return False, "Focus has been bypassed by current conditions."

        requirementsok, reason = self.checkcondition(focus.requirements)
        if not requirementsok:
            return False, reason

        availableok, reason = self.checkcondition(focus.availablecondition)
        if not availableok:
            return False, reason

        if focus.politicalpowercost:
            try:
                currentpp = int(self.dynamiccontext.get("political_power", self.dynamiccontext.get("player_political_power", 0)) or 0)
            except (TypeError, ValueError):
                currentpp = 0
            if currentpp < focus.politicalpowercost:
                return False, f"Requires {focus.politicalpowercost} political power."


        return True, ""



    #check for missing prerequisites
    def missingprerequisites(self, focusid: str):
        focus = self.focuses.get(focusid)
        if focus is None:
            return ()
        return tuple(prerequisite for prerequisite in focus.prerequisites if prerequisite not in self.completedids)

    def completedexclusivefocuses(self, focusid: str):
        blocked = self.exclusives.get(focusid, set()) & self.completedids
        return tuple(sorted(blocked))



    # view data for the ui
    def viewdata(self):
        focusviews = []
        for focus in self.focuses.values():
            canstart, reason = self.canstartfocus(focus.id)
            progress = self.progress.get(focus.id, 0)
            status = self.focusstatus(focus.id, canstart)
            focusviews.append(
                {
                    "id": focus.id,
                    "title": focus.title,
                    "description": focus.description,
                    "turnsrequired": focus.turncount,
                    "duration_days": focus.durationdays,
                    "focus_type": focus.focustype,
                    "political_power_cost": focus.politicalpowercost,
                    "branch": focus.branch,
                    "progress": int(math.floor(progress)),
                    "remainingturns": max(0, int(math.ceil(focus.turncount - progress))),
                    "prerequisites": list(focus.prerequisites),
                    "mutuallyexclusive": list(self.exclusives.get(focus.id, ())),
                    "requirements": dict(focus.requirements or {}),
                    "available_condition": dict(focus.availablecondition or {}),
                    "bypass_condition": dict(focus.bypasscondition or {}),
                    "cancel_conditions": dict(focus.cancelconditions or {}),
                    "effects": [dict(effect) for effect in focus.effects],
                    "icon": focus.icon,
                    "image": focus.image,
                    "x": focus.x,
                    "y": focus.y,
                    "status": status,
                    "canstart": canstart,
                    "blockingreason": reason,
                }
            )

        activefocus = self.focuses.get(self.activeid) if self.activeid else None
        return {
            "id": self.treeid,
            "country": self.country,
            "name": self.name,
            "cover_image": self.cover_image,
            "focuses": focusviews,
            "activefocusid": self.activeid,
            "activefocustitle": activefocus.title if activefocus else "",
            "activeturns": self.activeturns,
            "completedids": sorted(self.completedids),
            "failedids": sorted(self.failedids),
            "bypassedids": sorted(self.bypassedids),
            "lastmessage": self.lastmessage,
        }




    def savestate(self):
        return {
            "activefocusid": self.activeid,
            "activeturns": self.activeturns,
            "completedids": sorted(self.completedids),
            "failedids": sorted(self.failedids),
            "bypassedids": sorted(self.bypassedids),
            "progress": dict(self.progress),
        }
    def loadstate(self, state: Mapping[str, Any] | None):
        if not state:
            return

        completed = set(str(focusid) for focusid in state.get("completedids", ()))
        self.completedids = completed & set(self.focuses)
        failed = set(str(focusid) for focusid in state.get("failedids", ()))
        self.failedids = failed & set(self.focuses)
        bypassed = set(str(focusid) for focusid in state.get("bypassedids", ()))
        self.bypassedids = bypassed & set(self.focuses)

        progress = {}
        for focusid, amount in dict(state.get("progress", {})).items():
            if focusid in self.focuses:
                progress[focusid] = max(0.0, float(amount or 0))
        self.progress = progress

        activeid = state.get("activefocusid")
        if activeid in self.focuses and activeid not in self.completedids:
            self.activeid = activeid
            self.activeturns = max(0.0, float(state.get("activeturns", 0) or 0))
        else:
            self.activeid = None
            self.activeturns = 0.0







    # determine focus status for the ui
    # this directly links to coloring and availability in the ui, so it is important to keep this logic consistent and not add any additional status types without updating the ui accordingly
    def focusstatus(self, focusid: str, canstart: bool):
        if focusid in self.completedids:
            return "completed"
        if focusid in self.failedids:
            return "failed"
        if focusid in self.bypassedids:
            return "bypassed"
        if focusid == self.activeid:
            return "active"
        if self.completedexclusivefocuses(focusid):
            return "blocked"
        if self.missingprerequisites(focusid):
            return "locked"
        if canstart:
            return "available"
        return "waiting"

    def startresult(self, success: bool, focusid: str | None, reason: str):
        self.lastmessage = reason
        return FocusStartResult(success=success, focusid=focusid, reason=reason)
