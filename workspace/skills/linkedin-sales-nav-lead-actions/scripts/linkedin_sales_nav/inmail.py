"""InMail / Message compose automation (Sales Navigator lead profile)."""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from linkedin_sales_nav.common import (
    effective_cdp_endpoint,
    looks_like_linkedin_auth_wall,
    normalize_lead_url,
    validate_sales_lead_url,
)

# Message button on lead profile
MESSAGE_BUTTON_SELECTORS: tuple[str, ...] = (
    'button[aria-label*="Message" i]',
    'button:has-text("Message")',
    'a[aria-label*="Message" i]',
)

# Subject line in compose (tune when LinkedIn renames labels)
INMAIL_SUBJECT_SELECTORS: tuple[str, ...] = (
    'input[placeholder*="Subject (required)" i]',
    'input[placeholder*="Subject" i]',
    'input[aria-label*="Subject (required)" i]',
    'input[aria-label*="Subject" i]',
    'input[name="subject"]',
    'input[data-artdeco-is-focused][type="text"]',
)

# Body: observed 2026 DOM example:
# <textarea class="... _message-field_jrrmou _message-field--with-subject_jrrmou"
#   aria-label="Type your message here or draft with AI" id="compose-form-text-ember159"
#   name="message" ...>
# Prefer compound selectors; hash suffix on classes changes — keep *_message-field_* substrings.
INMAIL_BODY_SELECTORS: tuple[str, ...] = (
    # Exact-ish combinations (most specific first)
    'textarea[name="message"][class*="_message-field--with-subject_"][class*="_message-field_"]',
    'textarea[name="message"][class*="_message-field--with-subject_"]',
    'textarea[name="message"][aria-label*="Type your message here or draft with AI" i]',
    'textarea[name="message"][aria-label*="draft with AI" i]',
    'textarea[name="message"][aria-label*="Type your message" i]',
    'textarea[name="message"][id^="compose-form-text-ember"]',
    'textarea[id^="compose-form-text-ember"][name="message"]',
    # Class / label fallbacks (hash-rotates)
    'textarea[class*="_message-field--with-subject_"]',
    'textarea[class*="_message-field_"]',
    'textarea[aria-label*="draft with AI" i]',
    'textarea[aria-label*="Type your message" i]',
    'textarea[name="message"][placeholder*="Type your message" i]',
    'textarea[name="message"]',
    'textarea[id^="compose-form-text-ember"]',
    'textarea[placeholder*="Type your message" i]',
    'textarea[placeholder*="message" i]',
    'textarea[aria-label*="message" i]',
    # contenteditable fallback
    'div[placeholder*="Type your message" i]',
    'div[aria-label*="Type your message" i]',
    'div[role="textbox"][contenteditable="true"]',
    'div.msg-form__contenteditable[contenteditable="true"]',
    'div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"]',
)

INMAIL_SEND_SELECTORS: tuple[str, ...] = (
    'button[aria-label*="Send" i]:not([disabled])',
    'button:has-text("Send"):not([disabled])',
    'button[data-control-name*="send" i]:not([disabled])',
)


def inmail_compose_root(page: Any) -> Any:
    dialogs = page.locator('[role="dialog"]')
    try:
        n = min(dialogs.count(), 24)
    except Exception:
        n = 0
    for i in range(n):
        d = dialogs.nth(i)
        try:
            if not d.is_visible(timeout=400):
                continue
        except Exception:
            continue
        try:
            has_msg = (
                d.locator("textarea[class*=\"_message-field_\"]").count() > 0
                or d.locator('textarea[name="message"]').count() > 0
            )
            has_sub = d.locator('input[name="subject"]').count() > 0 or d.locator(
                'input[placeholder*="Subject" i]'
            ).count() > 0
        except Exception:
            continue
        if has_msg or has_sub:
            return d
    for sel in (
        ".artdeco-modal:has(textarea[name='message'])",
        ".artdeco-modal:has(textarea[class*='_message-field_'])",
        "[data-test-modal-container]:has(textarea[name='message'])",
    ):
        try:
            m = page.locator(sel).first
            if m.is_visible(timeout=600):
                return m
        except Exception:
            continue
    return page


def paste_text_into_textarea(el: Any, text: str) -> bool:
    try:
        if el.evaluate("node => node.tagName.toLowerCase()") != "textarea":
            return False
    except Exception:
        return False

    text = text or ""

    def _nonempty(val: str) -> bool:
        return bool((val or "").strip())

    try:
        el.scroll_into_view_if_needed(timeout=5000)
        el.click(timeout=5000)
        el.evaluate(
            "(node, t) => {"
            "  node.focus(); node.select();"
            "  const desc = Object.getOwnPropertyDescriptor("
            "    window.HTMLTextAreaElement.prototype, 'value');"
            "  const setter = desc ? desc.set : null;"
            "  if (setter) setter.call(node, t); else { node.value = t; }"
            "  node.dispatchEvent(new Event('input', { bubbles: true }));"
            "  node.dispatchEvent(new Event('change', { bubbles: true }));"
            "}",
            text,
        )
        if _nonempty(el.input_value(timeout=3000)):
            return True
    except Exception:
        pass

    try:
        el.click(timeout=5000)
        el.evaluate("(node) => { node.focus(); node.select(); }")
        el.fill(text)
        if _nonempty(el.input_value(timeout=2000)):
            return True
    except Exception:
        pass

    try:
        el.click(timeout=5000)
        el.evaluate("(node) => { node.focus(); node.select(); }")
        el.press_sequentially(text, delay=10)
        if _nonempty(el.input_value(timeout=2000)):
            return True
    except Exception:
        pass

    return False


def fill_inmail_body_in_root(root: Any, body: str) -> bool:
    for sel in INMAIL_BODY_SELECTORS:
        try:
            grouped = root.locator(sel)
            count = min(grouped.count(), 12)
        except Exception:
            continue
        for j in range(count):
            el = grouped.nth(j)
            try:
                if not el.is_visible(timeout=1800):
                    continue
                el.scroll_into_view_if_needed(timeout=5000)
                tag = el.evaluate("node => node.tagName.toLowerCase()")
            except Exception:
                continue

            if tag == "textarea":
                try:
                    el.click(timeout=5000)
                    el.fill(body)
                    if (el.input_value(timeout=2000) or "").strip():
                        return True
                except Exception:
                    pass
                if paste_text_into_textarea(el, body):
                    if (el.input_value(timeout=2000) or "").strip():
                        return True
                try:
                    el.click(timeout=5000)
                    el.evaluate("(node) => { node.focus(); node.select(); }")
                    el.press_sequentially(body, delay=8)
                    if (el.input_value(timeout=2000) or "").strip():
                        return True
                except Exception:
                    pass
            else:
                try:
                    el.click(timeout=5000)
                    el.fill("")
                    el.type(body, delay=15)
                    return True
                except Exception:
                    continue

    for pat in (
        re.compile(r"type\s+your\s+message", re.I),
        re.compile(r"draft\s+with\s+ai", re.I),
        re.compile(r"message\s+here", re.I),
        re.compile(r"here\s+or\s+draft", re.I),
    ):
        try:
            loc = root.get_by_role("textbox", name=pat).first
            if not loc.is_visible(timeout=2500):
                continue
            tag = loc.evaluate("node => node.tagName.toLowerCase()")
            if tag == "textarea":
                try:
                    loc.click(timeout=4000)
                    loc.fill(body)
                    if (loc.input_value(timeout=2000) or "").strip():
                        return True
                except Exception:
                    pass
                if paste_text_into_textarea(loc, body):
                    if (loc.input_value(timeout=2000) or "").strip():
                        return True
            else:
                loc.click(timeout=4000)
                loc.fill("")
                loc.type(body, delay=15)
                return True
        except Exception:
            continue

    return False


def send_inmail_message(
    profile_url: str,
    subject: str,
    body: str,
    *,
    timeout_ms: int = 60000,
    dry_run: bool = False,
    send: bool = True,
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

    if not subject or not subject.strip():
        return {"ok": False, "detail": "subject is required and must not be empty.", "profile_url": profile_url}
    if not body or not body.strip():
        return {"ok": False, "detail": "body is required and must not be empty.", "profile_url": profile_url}

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

    def _run_inmail_flow(page: Any) -> dict[str, Any]:
        inner: dict[str, Any] = {"ok": False, "detail": "unknown", "profile_url": u}

        page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_selector(
                ", ".join(MESSAGE_BUTTON_SELECTORS[:2]) + ", main h1",
                timeout=min(18000, timeout_ms),
            )
        except Exception:
            pass
        time.sleep(1.2)

        if looks_like_linkedin_auth_wall(page.url):
            inner["detail"] = (
                "Stopped at LinkedIn login / checkpoint — use an already-signed-in browser "
                "(--openclaw or --user-data-dir with Sales Nav logged in)."
            )
            return inner

        clicked_msg = False
        for sel in MESSAGE_BUTTON_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=3000):
                    loc.scroll_into_view_if_needed(timeout=3000)
                    loc.click(timeout=6000)
                    clicked_msg = True
                    break
            except Exception:
                continue

        if not clicked_msg:
            inner["detail"] = (
                "Could not find or click the Message button on this profile. "
                "The profile may not support InMail or the page did not load correctly."
            )
            return inner

        try:
            page.wait_for_selector(
                'input[placeholder*="Subject" i], '
                'textarea[aria-label*="draft with AI" i], '
                'textarea[aria-label*="Type your message here or draft with AI" i], '
                'textarea[aria-label*="Type your message" i], '
                'textarea[name="message"][class*="_message-field"], '
                'textarea[name="message"], textarea[class*="_message-field_"], '
                'textarea[id^="compose-form-text-ember"], '
                'div[contenteditable="true"]',
                timeout=min(14000, timeout_ms),
            )
        except Exception:
            pass
        time.sleep(0.65)
        compose = inmail_compose_root(page)

        filled_subject = False
        for sel in INMAIL_SUBJECT_SELECTORS:
            try:
                subj_el = compose.locator(sel).first
                if subj_el.is_visible(timeout=3000):
                    subj_el.click(timeout=4000)
                    subj_el.fill(subject)
                    time.sleep(0.35)
                    filled_subject = True
                    break
            except Exception:
                continue

        if not filled_subject:
            inner["detail"] = (
                "Message popup opened but could not locate the Subject field. "
                "LinkedIn UI may have changed — update INMAIL_SUBJECT_SELECTORS."
            )
            return inner

        filled_body = fill_inmail_body_in_root(compose, body)
        if not filled_body:
            filled_body = fill_inmail_body_in_root(page, body)

        if not filled_body:
            inner["detail"] = (
                "Subject filled but could not locate or fill the message body field "
                "(InMail textarea). LinkedIn UI may have changed — check INMAIL_BODY_SELECTORS "
                "in linkedin_sales_nav/inmail.py or compose detection (inmail_compose_root)."
            )
            return inner

        if dry_run or not send:
            inner["ok"] = True
            inner["detail"] = (
                f"{'dry_run' if dry_run else 'send=False'}: Subject and body filled; "
                "Send was NOT clicked."
            )
            return inner

        time.sleep(0.45)
        compose_send = inmail_compose_root(page)
        clicked_send = False
        for sel in INMAIL_SEND_SELECTORS:
            try:
                send_btn = compose_send.locator(sel).first
                if send_btn.is_visible(timeout=4000) and not send_btn.is_disabled():
                    send_btn.click(timeout=6000)
                    clicked_send = True
                    break
            except Exception:
                continue

        if not clicked_send:
            for sel in INMAIL_SEND_SELECTORS:
                try:
                    send_btn = page.locator(sel).first
                    if send_btn.is_visible(timeout=2500) and not send_btn.is_disabled():
                        send_btn.click(timeout=6000)
                        clicked_send = True
                        break
                except Exception:
                    continue

        if not clicked_send:
            try:
                fb = compose_send.locator('button:has-text("Send")').first
                if fb.is_visible(timeout=2000):
                    fb.click(force=True, timeout=5000)
                    clicked_send = True
            except Exception:
                pass

        if not clicked_send:
            try:
                fb = page.locator('button:has-text("Send")').first
                if fb.is_visible(timeout=2000):
                    fb.click(force=True, timeout=5000)
                    clicked_send = True
            except Exception:
                pass

        if not clicked_send:
            inner["detail"] = (
                "Subject and body filled but could not click Send. "
                "The button may still be disabled (try a longer settle delay) or the UI changed."
            )
            return inner

        try:
            page.wait_for_selector(
                'input[placeholder*="Subject" i]',
                state="hidden",
                timeout=8000,
            )
        except Exception:
            pass

        inner["ok"] = True
        inner["detail"] = f"InMail sent. Subject: '{subject}'."
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
                return _run_inmail_flow(page_oc)
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
            return _run_inmail_flow(page)
        except PwTimeout as e:
            return {"ok": False, "detail": f"Timeout: {e}", "profile_url": u}
        finally:
            context.close()
