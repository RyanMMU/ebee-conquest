import sys
from pathlib import Path

if sys.version_info[:3] == (3, 9, 0):
    # python 3.9.0 has a typing bug where collections.abc.Callable[[]] is unhashable
    # pygame imports that form during module import, so patch it before any pygame import.
    # from https://bugs.python.org/issue43004
    # from https://github.com/python/cpython/issues/87170
    # https://stackoverflow.com/questions/65858528/is-collections-abc-callable-bugged-in-python-3-9-1
    # switching to pygame-ce and python 3.10+

    import collections.abc as _collections_abc
    from typing import Callable as _typing_callable

    _collections_abc.Callable = _typing_callable

_project_root = Path(__file__).resolve().parent.parent #ebee conquest root
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from engine.api import EbeeEngine
from engine.events import EngineEventType, EventBus

__all__ = ["EbeeEngine", "EngineEventType", "EventBus"]


