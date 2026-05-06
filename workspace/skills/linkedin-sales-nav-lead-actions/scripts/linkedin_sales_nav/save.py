"""Save lead to a Sales Navigator list."""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from linkedin_sales_nav.common import (
    effective_cdp_endpoint,
    looks_like_linkedin_auth_wall,
    normalize_lead_url,
    try_click,
    validate_sales_lead_url,
)

DEFAULT_LIST_NAME = "Agent's Lead List"


def save_lead_to_list(
    profile_url: str,
    list_name: str = DEFAULT_LIST_NAME,
    *,
    timeout_ms: int = 55000,
    dry_run: bool = False,
    user_data_dir: Optional[str] = None,
    cdp_url: Optional[str] = None,
    use_openclaw_browser: bool = False,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    except ImportError:
        return {
            "ok": False,
            "detail": "Playwright missing. Run: pip3 install playwright && python3 -m playwright install chromium",
            "profile_url": profile_url,
        }

    u = normalize_lead_url(profile_url)
    err = validate_sales_lead_url(u)
    if err:
        return {"ok": False, "detail": err, "profile_url": profile_url}

    resolved_cdp = effective_cdp_endpoint(
        use_openclaw_browser=use_openclaw_browser, cdp_url=cdp_url
    )

    if user_data_dir and resolved_cdp:
        return {
            "ok": False,
            "detail": "Pass either user_data_dir or CDP/OpenClaw connection, not both.",
            "profile_url": u,
        }

    def _run_save_flow(page: Any) -> dict[str, Any]:
        inner: dict[str, Any] = {"ok": False, "detail": "unknown", "profile_url": u}

        page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_selector(
                'button[aria-label*="Message" i], main h1',
                timeout=min(15000, timeout_ms),
            )
        except Exception:
            pass
        time.sleep(1.0)

        if looks_like_linkedin_auth_wall(page.url):
            inner["detail"] = (
                "Stopped at LinkedIn login / checkpoint — use an already-signed-in browser "
                "(--openclaw or --user-data-dir with Sales Nav logged in)."
            )
            return inner

        save_btn_candidates = [
            'button[aria-label*="Add to a custom list" i]',
            'button[aria-label*="saved. Add" i]',
            'button[aria-label$="saved" i]',
            'button[aria-label^="Save " i]',
            "button:has-text('Saved')",
            "button:has-text('Save')",
        ]
        clicked_save = False
        for sel in save_btn_candidates:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    loc.scroll_into_view_if_needed(timeout=3000)
                    loc.click(timeout=5000)
                    clicked_save = True
                    break
            except Exception:
                continue

        if not clicked_save:
            inner["detail"] = (
                "Could not find the Save / Saved button on this profile. "
                "UI may have changed or the lead page did not fully load."
            )
            return inner

        time.sleep(0.8)

        dropdown = None
        for container_sel in [
            "[role='dialog']",
            "[role='listbox']",
            "[role='menu']",
        ]:
            try:
                loc = page.locator(container_sel).first
                if loc.is_visible(timeout=4000):
                    dropdown = loc
                    break
            except Exception:
                continue

        if dropdown is None:
            try:
                dropdown = page.locator("div").filter(
                    has_text=re.compile(r"^add to list$", re.I)
                ).last
                if not dropdown.is_visible(timeout=3000):
                    dropdown = None
            except Exception:
                dropdown = None

        if dropdown is None:
            inner["detail"] = (
                "Save button clicked but the 'Add to list' dropdown did not appear. "
                "The lead may have been unsaved instead — check profile state."
            )
            return inner

        if dry_run:
            inner["ok"] = True
            inner["detail"] = f"dry_run: dropdown found; would pick list '{list_name}'."
            return inner

        list_pattern = re.compile(re.escape(list_name), re.I)
        list_candidates = [
            dropdown.get_by_role("option", name=list_pattern),
            dropdown.get_by_role("menuitem", name=list_pattern),
            dropdown.get_by_role("button", name=list_pattern),
            dropdown.locator("li").filter(has_text=list_pattern),
            dropdown.locator("[role='listitem']").filter(has_text=list_pattern),
            dropdown.locator("span").filter(has_text=list_pattern),
        ]
        for c in list_candidates:
            try:
                item = c.first
                if item.is_visible(timeout=2000):
                    if try_click(item) or try_click(item, force=True):
                        time.sleep(0.5)
                        inner["ok"] = True
                        inner["detail"] = f"Lead saved to list '{list_name}'."
                        return inner
            except Exception:
                continue

        inner["detail"] = (
            f"Dropdown opened but could not find list '{list_name}' inside it. "
            "Check the exact list name and try again."
        )
        return inner

    with sync_playwright() as p:
        if resolved_cdp:
            browser_oc = None
            page_oc = None
            try:
                browser_oc = p.chromium.connect_over_cdp(resolved_cdp)
                if not browser_oc.contexts:
                    return {
                        "ok": False,
                        "detail": (
                            "No browser contexts over CDP. Start OpenClaw browser first:\n"
                            "  openclaw browser --browser-profile openclaw start"
                        ),
                        "profile_url": u,
                    }
                context_oc = browser_oc.contexts[0]
                page_oc = context_oc.new_page()
            except Exception as ex:
                return {"ok": False, "detail": f"CDP connect failed ({resolved_cdp}): {ex}", "profile_url": u}
            try:
                return _run_save_flow(page_oc)
            except PwTimeout as e:
                return {"ok": False, "detail": f"Timeout: {e}", "profile_url": u}
            except Exception as ex:
                return {"ok": False, "detail": f"Automation failed: {ex}", "profile_url": u}
            finally:
                if page_oc:
                    try:
                        page_oc.close()
                    except Exception:
                        pass
                if browser_oc:
                    try:
                        browser_oc.close()
                    except Exception:
                        pass

        if user_data_dir:
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                slow_mo=75,
                viewport={"width": 1400, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=75,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()

        try:
            return _run_save_flow(page)
        except PwTimeout as e:
            return {"ok": False, "detail": f"Timeout: {e}", "profile_url": u}
        finally:
            context.close()
