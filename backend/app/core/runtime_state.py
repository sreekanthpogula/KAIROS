"""Tiny shared mutable state between app.main's lifespan and the health
endpoint. Split out to avoid a circular import (main imports the health
router; health needs to read what main's lifespan set)."""
from __future__ import annotations

startup_error: str | None = None
