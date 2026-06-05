from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping

# FOCUS EFFECTS MODULE
# add more effects here and register them in createeffectregistry() to make them available for use in focus trees


class FocusEffectError(ValueError):
    """Raised when focus effect data cannot be applied."""


@dataclass
class FocusEffectContext:
    gold: int = 0 #placeholder
    population: int = 0
    economyconfig: MutableMapping[str, Any] | None = None
    country: str | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def __post_init__(self): # ensure economyconfig is a dict if not provided
        if self.economyconfig is None:
            self.economyconfig = {}


EffectHandler = Callable[[Mapping[str, Any], FocusEffectContext], None]



# registry for focus effects
class FocusEffectRegistry:
    def __init__(self):
        self.handlers: dict[str, EffectHandler] = {}


    # register a focus effect handler for a given effect type
    def register(self, effecttype: str, handler: EffectHandler):
        effectkey = str(effecttype or "").strip()
        if not effectkey:
            raise FocusEffectError("Focus effect type cannot be empty.")
        self.handlers[effectkey] = handler

    def apply(self, effects, context: FocusEffectContext):
        appliedeffects = []
        if context.metadata.get("requires_legislature") and not context.metadata.get("law_passed", True):
            return [
                {
                    "type": "domestic_law_check",
                    "result": "blocked",
                    "passing_chance": int(context.metadata.get("law_passing_chance", 0) or 0),
                    "roll": int(context.metadata.get("law_roll", 0) or 0),
                }
            ]

        for effect in effects or ():
            if not isinstance(effect, Mapping):
                raise FocusEffectError(f"Focus effect must be a mapping, got {type(effect).__name__}.")

            effecttype = str(effect.get("type", "")).strip()
            handler = self.handlers.get(effecttype)
            if handler is None:
                raise FocusEffectError(f"Unknown focus effect type: {effecttype}")

            handler(effect, context)
            appliedeffects.append(dict(effect))

        return appliedeffects


def readint(effect: Mapping[str, Any], key: str, default=0):
    try:
        return int(effect.get(key, default))
    except (TypeError, ValueError) as error:
        raise FocusEffectError(f"Focus effect field '{key}' must be an integer.") from error


def readfloat(effect: Mapping[str, Any], key: str, default=0.0):
    try:
        return float(effect.get(key, default))
    except (TypeError, ValueError) as error:
        raise FocusEffectError(f"Focus effect field '{key}' must be a number.") from error


def clampvalue(value, lower=0.0, upper=100.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = lower
    return max(lower, min(upper, number))



# CURRENT FOCUS EFFECTS:
def modifygold(effect: Mapping[str, Any], context: FocusEffectContext):
    # concept: modify gold by a certain amount (positive or negative)
    context.gold += readint(effect, "amount")

def modifypopulationgrowth(effect: Mapping[str, Any], context: FocusEffectContext):
    # concept: modify population growth bonus by a certain amount (positive or negative)
    amount = readint(effect, "amount")
    currentbonus = readint(context.economyconfig, "populationgrowthbonus")
    context.economyconfig["populationgrowthbonus"] = currentbonus + amount


def modifydomesticvariable(effect: Mapping[str, Any], context: FocusEffectContext):
    countrydata = context.metadata.get("domestic_country") if context.metadata else None
    if not isinstance(countrydata, MutableMapping):
        return
    key = str(effect.get("key") or effect.get("variable") or "").strip()
    if not key:
        raise FocusEffectError("Domestic variable effect requires a key.")
    amount = readfloat(effect, "amount")
    lower = readfloat(effect, "min", 0.0)
    upper = readfloat(effect, "max", 100.0)
    countrydata[key] = clampvalue(countrydata.get(key, 0.0) + amount, lower, upper)


def setdomesticvalue(effect: Mapping[str, Any], context: FocusEffectContext):
    countrydata = context.metadata.get("domestic_country") if context.metadata else None
    if not isinstance(countrydata, MutableMapping):
        return
    key = str(effect.get("key") or effect.get("variable") or "").strip()
    if not key:
        raise FocusEffectError("Set domestic value effect requires a key.")
    countrydata[key] = effect.get("value")


def setdomesticflag(effect: Mapping[str, Any], context: FocusEffectContext):
    countrydata = context.metadata.get("domestic_country") if context.metadata else None
    if not isinstance(countrydata, MutableMapping):
        return
    flag = str(effect.get("flag") or effect.get("key") or "").strip()
    if not flag:
        raise FocusEffectError("Domestic flag effect requires a flag.")
    countrydata[flag] = bool(effect.get("value", True))




# UPDATE THIS FUNCTION TO REGISTER NEW EFFECTS
def createeffectregistry():
    registry = FocusEffectRegistry()
    registry.register("modify_gold", modifygold)
    registry.register("modify_population_growth", modifypopulationgrowth)
    registry.register("modify_domestic_variable", modifydomesticvariable)
    registry.register("set_domestic_value", setdomesticvalue)
    registry.register("set_domestic_flag", setdomesticflag)
    return registry
