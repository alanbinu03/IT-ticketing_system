#!/usr/bin/env python3
"""Run development seed. Usage from repo root: python scripts/seed.py"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend))
runpy.run_module("app.database.seed", run_name="__main__")
