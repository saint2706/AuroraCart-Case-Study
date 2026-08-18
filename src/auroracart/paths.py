"""Filesystem locations, resolved once so nothing else has to guess.

Every path below is derived from this file's own location, so the project works
from any working directory — repo root, ``notebooks/``, or a Render container.
``AURORACART_DATA_DIR`` overrides the data root if the CSV lives elsewhere
(e.g. mounted at deploy time rather than committed).
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
"""``src/auroracart`` — also where Dash looks for ``assets/``."""

PROJECT_ROOT = PACKAGE_DIR.parents[1]
"""Repository root (``src/auroracart`` -> ``src`` -> root)."""

DATA_DIR = Path(os.environ.get("AURORACART_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_DATA_PATH = RAW_DATA_DIR / "data-AuroraCart.csv"
"""The case's ``data.csv``, kept under its original export name."""

ASSETS_DIR = PACKAGE_DIR / "assets"
DOCS_DIR = PROJECT_ROOT / "docs"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"
FIGURES_DIR = DELIVERABLES_DIR / "figures"

__all__ = [
    "PACKAGE_DIR",
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "RAW_DATA_PATH",
    "ASSETS_DIR",
    "DOCS_DIR",
    "NOTEBOOKS_DIR",
    "DELIVERABLES_DIR",
    "FIGURES_DIR",
]
