"""Shared URLs, guards, clicks, CDP resolution (no Playwright imports at module level required)."""

from __future__ import annotations

import os
import re
from typing import Any, Optional

DEFAULT_OPENCLAW_CDP_URL = "http://127.0.0.1:18800"


def effective_cdp_endpoint(
    *, use_openclaw_browser: bool, cdp_url: Optional[str]
) -> str:
    """Resolved CDP URL string; empty if not using CDP/OpenClaw path."""
    r = (cdp_url or "").strip()
    if use_openclaw_browser and not r:
        r = os.environ.get(
            "OPENCLAW_BROWSER_CDP_URL", DEFAULT_OPENCLAW_CDP_URL
        ).strip()
    return r


def looks_like_linkedin_auth_wall(url: str) -> bool:
    u = url.lower()
    if "linkedin.com" not in u:
        return False
    return (
        "/login" in u
        or "/uas/" in u
        or "/checkpoint/" in u
        or "/sales/login" in u
    )


def normalize_lead_url(raw: str) -> str:
    u = raw.strip()
    if not u:
        return u
    if u.startswith("//"):
        u = "https:" + u
    elif not re.match(r"^https?://", u, flags=re.I):
        u = "https://" + u
    return u


def validate_sales_lead_url(u: str) -> Optional[str]:
    """Return None if OK, else English error fragment."""
    if "linkedin.com" not in u.lower() or "/sales/" not in u.lower():
        return "Expected a LinkedIn Sales Navigator URL (must contain linkedin.com and /sales/)."
    return None


def try_click(locator: Any, *, force: bool = False) -> bool:
    try:
        locator.scroll_into_view_if_needed(timeout=5000)
        locator.click(timeout=8000, force=force)
        return True
    except Exception:
        return False
