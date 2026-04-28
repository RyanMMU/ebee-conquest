from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping


class FocusEffectError(ValueError):
    """Raised when focus effect data cannot be applied."""


@dataclass
class FocusEffectContext:
    gold: int = 0
    population: int = 0
    economyconfig: MutableMapping[str, Any] | None = None
    country: str | None = None
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.economyconfig is None:
            self.economyconfig = {}


EffectHandler = Callable[[Mapping[str, Any], FocusEffectContext], None]


class FocusEffectRegistry:
    def __init__(self):
        self.handlers: dict[str, EffectHandler] = {}

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


def modifygold(effect: Mapping[str, Any], context: FocusEffectContext):
    context.gold += readint(effect, "amount")


def modifypopulationgrowth(effect: Mapping[str, Any], context: FocusEffectContext):
    amount = readint(effect, "amount")
    currentbonus = readint(context.economyconfig, "populationgrowthbonus")
    context.economyconfig["populationgrowthbonus"] = currentbonus + amount


def createeffectregistry():
    registry = FocusEffectRegistry()
    registry.register("modify_gold", modifygold)
    registry.register("modify_population_growth", modifypopulationgrowth)
    return registry
