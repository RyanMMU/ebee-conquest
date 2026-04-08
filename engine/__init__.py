import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent #ebee conquest root
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from engine.api import EbeeEngine

__all__ = ["EbeeEngine"] 
