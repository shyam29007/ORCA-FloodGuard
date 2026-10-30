"""ORAC-FloodGuard Backend Application Package."""

import sys
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent)
_root_dir = str(Path(__file__).resolve().parent.parent.parent)

for path in [_backend_dir, _root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

__version__ = "1.0.0"

