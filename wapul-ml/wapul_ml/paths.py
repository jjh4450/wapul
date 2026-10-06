"""Project folders: the data repo clone, caches and logs, trained models."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = ROOT / "cache"
MODELS = ROOT / "models"
