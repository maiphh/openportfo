"""Pytest isolation: do not load backend/.env into Settings."""

from __future__ import annotations

import os

# Set before any test imports Settings / create_app.
os.environ["OPENPORTFO_DISABLE_ENV_FILE"] = "1"
