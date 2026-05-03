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



# CURRENT FOCUS EFFECTS:
def modifygold(effect: Mapping[str, Any], context: FocusEffectContext):
    # concept: modify gold by a certain amount (positive or negative)
    context.gold += readint(effect, "amount")

def modifypopulationgrowth(effect: Mapping[str, Any], context: FocusEffectContext):
    # concept: modify population growth bonus by a certain amount (positive or negative)
    amount = readint(effect, "amount")
    currentbonus = readint(context.economyconfig, "populationgrowthbonus")
    context.economyconfig["populationgrowthbonus"] = currentbonus + amount




# UPDATE THIS FUNCTION TO REGISTER NEW EFFECTS
def createeffectregistry():
    registry = FocusEffectRegistry()
    registry.register("modify_gold", modifygold)
    registry.register("modify_population_growth", modifypopulationgrowth)
    return registry
