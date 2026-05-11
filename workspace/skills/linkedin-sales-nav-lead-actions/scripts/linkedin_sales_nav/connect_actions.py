"""Connection request automation (overflow … → Connect → invite modal)."""

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

PRIMARY_CONNECT_NAME = re.compile(r"^\s*connect\s*$", re.I)
MENU_CONNECT_TEXT = re.compile(r"^\s*connect\s*$", re.I)

OVERFLOW_BUTTON_SELECTOR_CANDIDATES: tuple[str, ...] = (
    'button[data-x--lead-actions-bar-overflow-menu]',
    'button[aria-label*="Open actions overflow menu" i]',
    'button[aria-label*="overflow menu" i]',
    'button[aria-label*="overflow" i]',
    "button[data-control-name*='overflow' i]",
    "button[data-control-name*='more' i]",
    "button.artdeco-dropdown__trigger",
    'button[aria-label*="More actions" i]',
    'button[aria-label*="more actions" i]',
    'button[aria-label*="Show more actions" i]',
    'button[aria-haspopup="true"][aria-expanded]',
    "button:has(svg)",
)

MODAL_SEND_WITHOUT_NOTE = (
    "button:has-text('Send without a note')",
    "button:has-text('Send Without a Note')",
)
MODAL_SEND_INVITE = (
    "button:has-text('Send Invitation')",
    "button:has-text('Send invitation')",
    "button:has-text('Send')",
    "button[data-control-name*='send_invite' i]",
)
NOTE_TEXTAREA = (
    "textarea[name='message']",
    "textarea#custom-message",
    "textarea.connect-button-send-invite__custom-message",
    "div[contenteditable='true'][role='textbox']",
)


def _open_overflow_menu(page: Any, timeout_ms: int) -> bool:
    # Prioritize the most stable data attribute selector
    try:
        btn = page.locator('button[data-x--lead-actions-bar-overflow-menu]').first
        if btn.is_visible(timeout=3000):
            if try_click(btn, force=False) or try_click(btn, force=True):
                time.sleep(0.5)
                return True
    except Exception:
        pass

    for sel in OVERFLOW_BUTTON_SELECTOR_CANDIDATES:
        try:
            loc = page.locator(sel)
            n = min(loc.count(), 8)
            for i in range(n):
                btn = loc.nth(i)
                if not btn.is_visible(timeout=1500):
                    continue
                al = (btn.get_attribute("aria-label") or "").lower()
                # Only filter out obvious Message buttons if they aren't the overflow
                if "message" in al and "more" not in al and "overflow" not in al:
                    continue
                if try_click(btn, force=False) or try_click(btn, force=True):
                    time.sleep(0.4)
                    return True
        except Exception:
            continue

    try:
        header_actions = page.locator(
            "section, header, div"
        ).filter(has=page.get_by_role("button", name=re.compile(r"^message$", re.I)))
        row_btns = header_actions.locator("button").filter(has_text=re.compile(r"^$"))
        if row_btns.count() == 0:
            row_btns = header_actions.locator("button")
        for i in range(min(row_btns.count(), 12)):
            b = row_btns.nth(i)
            if not b.is_visible(timeout=1000):
                continue
            txt = (b.inner_text() or "").strip().lower()
            al = (b.get_attribute("aria-label") or "").lower()
            if txt == "message":
                continue
            if "message" in txt or "save" in txt or "follow" in txt:
                continue
            if len(txt) < 2 and ("more" in al or "actions" in al or b.locator("svg").count() > 0):
                if try_click(b, force=False) or try_click(b, force=True):
                    time.sleep(0.4)
                    return True
    except Exception:
        pass

    return False


def _click_menu_connect(page: Any, timeout_ms: int) -> bool:
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        candidates: list[Any] = [
            page.get_by_role("menuitem", name=MENU_CONNECT_TEXT),
            page.get_by_role("button", name=MENU_CONNECT_TEXT),
            page.locator("div[role='button']:visible").filter(has_text=MENU_CONNECT_TEXT),
            page.locator("a:visible").filter(has_text=MENU_CONNECT_TEXT),
            page.locator("span:visible").filter(has_text=MENU_CONNECT_TEXT),
        ]
        for c in candidates:
            try:
                loc = c.first
                if loc.is_visible(timeout=800):
                    if try_click(loc, force=False) or try_click(loc, force=True):
                        return True
            except Exception:
                continue
        time.sleep(0.2)
    return False


def _click_primary_connect(page: Any, timeout_ms: int) -> bool:
    try:
        loc = page.get_by_role("button", name=PRIMARY_CONNECT_NAME).first
        if loc.is_visible(timeout=timeout_ms):
            return try_click(loc) or try_click(loc, force=True)
    except Exception:
        pass
    return False


def _submit_invite_modal(page: Any, note: Optional[str], timeout_ms: int, dry_run: bool) -> bool:
    try:
        time.sleep(0.5)
        if dry_run:
            return True

        if note:
            for sel in NOTE_TEXTAREA:
                try:
                    box = page.locator(sel).first
                    if box.is_visible(timeout=3000):
                        box.click()
                        box.fill(note)
                        break
                except Exception:
                    continue

        modal_groups = (
            (MODAL_SEND_INVITE, MODAL_SEND_WITHOUT_NOTE)
            if note
            else (MODAL_SEND_INVITE, MODAL_SEND_WITHOUT_NOTE)
        )

        for group in modal_groups:
            for sel in group:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2500):
                        if try_click(btn) or try_click(btn, force=True):
                            # Wait for modal to dismiss — confirms invite was submitted
                            try:
                                page.wait_for_selector(
                                    "[role='dialog']",
                                    state="hidden",
                                    timeout=8000,
                                )
                            except Exception:
                                # Modal may have already closed or selector differs — give a
                                # generous fixed delay as fallback so the network request lands
                                time.sleep(3)
                            else:
                                # Extra buffer after modal closes for the XHR to complete
                                time.sleep(1)
                            return True
                except Exception:
                    continue
        return False
    except Exception:
        return False


def send_sales_nav_connection_request(
    profile_url: str,
    *,
    note: Optional[str] = None,
    headless: bool = False,
    slow_mo_ms: int = 75,
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

    result: dict[str, Any] = {"ok": False, "detail": "unknown", "profile_url": u}

    def _run_connect_flow(page_inner: Any) -> dict[str, Any]:
        inner: dict[str, Any] = {"ok": False, "detail": "unknown", "profile_url": u}
        page_inner.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
        
        # Wait for the overflow menu button to appear before proceeding
        try:
            page_inner.wait_for_selector('button[data-x--lead-actions-bar-overflow-menu]', timeout=10000)
        except Exception:
            pass

        if looks_like_linkedin_auth_wall(page_inner.url):
            inner["detail"] = (
                "Stopped at LinkedIn login / checkpoint — use an already-signed-in browser "
                "(--openclaw or --user-data-dir with Sales Nav logged in)."
            )
            return inner

        if _click_primary_connect(page_inner, timeout_ms=8000):
            inner["ok"] = _submit_invite_modal(
                page_inner, note, timeout_ms, dry_run
            ) or dry_run
            inner["detail"] = (
                "Clicked primary Connect and submitted modal (or dry_run)."
                if inner["ok"]
                else "Clicked Connect but could not complete invite modal."
            )
            return inner

        if not _open_overflow_menu(page_inner, timeout_ms=timeout_ms):
            inner["detail"] = (
                "Could not open the profile overflow (…) menu. UI may have changed or "
                "Connect is unavailable (pending, already connected, or restricted)."
            )
            return inner

        if not _click_menu_connect(page_inner, timeout_ms=12000):
            inner["detail"] = (
                "Overflow opened but no Connect entry found (already connected, pending, or different UI)."
            )
            return inner

        inner["ok"] = (
            _submit_invite_modal(page_inner, note, timeout_ms, dry_run) or dry_run
        )
        inner["detail"] = (
            "Opened … menu, clicked Connect, and submitted invite (or dry_run)."
            if inner["ok"]
            else "Clicked menu Connect but could not complete invite modal."
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
                return {
                    "ok": False,
                    "detail": f"CDP connect failed ({resolved_cdp}): {ex}",
                    "profile_url": u,
                }

            try:
                return _run_connect_flow(page_oc)
            except PwTimeout as e:
                return {
                    "ok": False,
                    "detail": f"Timeout: {e}",
                    "profile_url": u,
                }
            except Exception as ex:
                return {
                    "ok": False,
                    "detail": f"Automation failed: {ex}",
                    "profile_url": u,
                }
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

        browser = None
        if user_data_dir:
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                slow_mo=slow_mo_ms,
                viewport={"width": 1400, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = p.chromium.launch(
                headless=headless,
                slow_mo=slow_mo_ms,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()

        try:
            return _run_connect_flow(page)
        except PwTimeout as e:
            result["detail"] = f"Timeout: {e}"
            return result
        finally:
            if user_data_dir:
                context.close()
            else:
                context.close()
                if browser:
                    browser.close()



