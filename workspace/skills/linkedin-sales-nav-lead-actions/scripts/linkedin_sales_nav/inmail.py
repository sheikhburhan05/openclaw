"""InMail / Message compose automation (Sales Navigator lead profile)."""

from __future__ import annotations

import os
import re
import sys
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
    # Do not use :not([disabled]) here — LinkedIn toggles disabled/aria-disabled after fill;
    # we wait for an enabled control in click_inmail_send_button.
    'button[aria-label*="Send InMail" i]',
    'button[aria-label*="Send message" i]',
    'button[aria-label*="Send" i]',
    'button[data-control-name*="send_message" i]',
    'button[data-control-name*="send" i]',
    'button.msg-form__send-button',
    'button[class*="msg-form__send"]',
    'button[type="submit"]',
    'button.artdeco-button--primary:has-text("Send")',
    'button:has-text("Send")',
    'footer button.artdeco-button--primary',
    'button[type="submit"]',
)


def _inmail_flow_debug_enabled() -> bool:
    v = (os.environ.get("LINKEDIN_SN_INMAIL_DEBUG") or "").strip().lower()
    return v in ("1", "true", "yes", "on", "debug")


def _inmail_flow_log(message: str) -> None:
    if not _inmail_flow_debug_enabled():
        return
    stamp = time.strftime("%H:%M:%S")
    print(f"[linkedin_sales_nav:inmail {stamp}] {message}", file=sys.stderr, flush=True)


def _inmail_flow_log_compose_probe(page: Any, label: str) -> None:
    if not _inmail_flow_debug_enabled():
        return
    _inmail_flow_log(f"{label} url={page.url!r}")
    probes: tuple[tuple[str, str], ...] = (
        ("dialog[role=dialog]", '[role="dialog"]'),
        ("textarea[name=message]", 'textarea[name="message"]'),
        ("textarea._message-field_*", 'textarea[class*="_message-field_"]'),
        ("subject input", 'input[placeholder*="Subject" i]'),
        ("compose-form-text-ember", 'textarea[id^="compose-form-text-ember"]'),
        ("contenteditable div", 'div[contenteditable="true"]'),
    )
    for name, sel in probes:
        try:
            n = page.locator(sel).count()
            _inmail_flow_log(f"  probe {name}: count={n}")
        except Exception as ex:
            _inmail_flow_log(f"  probe {name}: error {type(ex).__name__}: {ex}")


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


def _inmail_send_button_candidates(root: Any, sel: str) -> list[Any]:
    out: list[Any] = []
    try:
        if sel.strip().startswith("footer "):
            loc = root.locator(sel)
            n = min(loc.count(), 12)
            for i in range(n - 1, -1, -1):
                out.append(loc.nth(i))
            return out
        out.append(root.locator(sel).first)
    except Exception:
        pass
    return out


def _locator_seems_send_enabled(loc: Any) -> bool:
    try:
        if loc.is_disabled():
            return False
    except Exception:
        pass
    try:
        return bool(
            loc.evaluate(
                "(n) => !!(n && n.isConnected && !n.disabled && "
                "n.getAttribute('aria-disabled') !== 'true')"
            )
        )
    except Exception:
        return True


def click_inmail_send_button(
    *roots: Any,
    poll_s: float = 0.2,
    max_wait_s: float = 14.0,
) -> tuple[bool, Optional[str]]:
    """Find and click the InMail / message Send control (polls until enabled)."""
    deadline = time.monotonic() + max_wait_s
    send_label_re = re.compile(r"\bsend\b", re.I)

    while time.monotonic() < deadline:
        for root in roots:
            if root is None:
                continue
            for sel in INMAIL_SEND_SELECTORS:
                for loc in _inmail_send_button_candidates(root, sel):
                    try:
                        if not loc.is_visible(timeout=1200):
                            continue
                        if not _locator_seems_send_enabled(loc):
                            continue
                        try:
                            loc.click(timeout=6000)
                        except Exception:
                            loc.click(force=True, timeout=6000)
                        return True, sel
                    except Exception:
                        continue

            try:
                btn = root.get_by_role("button", name=re.compile(r"send", re.I)).first
                if btn.is_visible(timeout=1200) and _locator_seems_send_enabled(btn):
                    try:
                        btn.click(timeout=6000)
                    except Exception:
                        btn.click(force=True, timeout=6000)
                    return True, 'get_by_role("button", name=/send/i)'
            except Exception:
                pass

            try:
                btns = root.locator(
                    "button.artdeco-button--primary, "
                    "button.artdeco-button.artdeco-button--2"
                )
                for j in range(min(btns.count(), 24) - 1, -1, -1):
                    b = btns.nth(j)
                    try:
                        if not b.is_visible(timeout=500):
                            continue
                        txt = (b.inner_text(timeout=1200) or "").strip().replace("\n", " ")
                        if not send_label_re.match(txt):
                            continue
                        if not _locator_seems_send_enabled(b):
                            continue
                        try:
                            b.click(timeout=6000)
                        except Exception:
                            b.click(force=True, timeout=6000)
                        return True, f"artdeco primary text={txt!r}"
                    except Exception:
                        continue
            except Exception:
                pass

        time.sleep(poll_s)

    return False, None


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
        try:
            el.click(timeout=5000)
        except Exception:
            el.click(force=True, timeout=5000)
        el.evaluate(
            "(node, t) => {"
            "  node.focus(); node.select();"
            "  const desc = Object.getOwnPropertyDescriptor("
            "    window.HTMLTextAreaElement.prototype, 'value');"
            "  const setter = desc ? desc.set : null;"
            "  if (setter) setter.call(node, t); else { node.value = t; }"
            "  node.dispatchEvent(new Event('input', { bubbles: true }));"
            "  node.dispatchEvent(new Event('change', { bubbles: true }));"
            "  node.dispatchEvent(new Event('blur', { bubbles: true }));"
            "  node.dispatchEvent(new Event('focus', { bubbles: true }));"
            "}",
            text,
        )
        if _nonempty(el.input_value(timeout=3000)):
            return True
    except Exception:
        pass

    try:
        try:
            el.click(timeout=5000)
        except Exception:
            el.click(force=True, timeout=5000)
        el.evaluate("(node) => { node.focus(); node.select(); }")
        el.fill(text)
        if _nonempty(el.input_value(timeout=2000)):
            return True
    except Exception:
        pass

    try:
        try:
            el.click(timeout=5000)
        except Exception:
            el.click(force=True, timeout=5000)
        el.evaluate("(node) => { node.focus(); node.select(); }")
        el.press_sequentially(text, delay=10)
        if _nonempty(el.input_value(timeout=2000)):
            return True
    except Exception:
        pass

    return False


def fill_inmail_body_in_root(root: Any, body: str) -> bool:
    _layout_visible_js = """(node) => {
          if (!node || !node.isConnected) return false;
          const s = window.getComputedStyle(node);
          if (s.display === 'none' || s.visibility === 'hidden') return false;
          const r = node.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        }"""

    for sel in INMAIL_BODY_SELECTORS:
        try:
            grouped = root.locator(sel)
            count = min(grouped.count(), 12)
        except Exception:
            continue
        for j in range(count):
            el = grouped.nth(j)
            try:
                # Prefer Playwright visibility, but accept in-layout nodes for message fields
                # (Sales Nav / Ember often hide the native textarea while a layer shows the UI).
                visible = el.is_visible(timeout=1800)
                try:
                    ok_layout = bool(el.evaluate(_layout_visible_js))
                except Exception:
                    ok_layout = False
                if not visible and not ok_layout:
                    continue
                el.scroll_into_view_if_needed(timeout=5000)
                tag = el.evaluate("node => node.tagName.toLowerCase()")
            except Exception:
                continue

            if tag == "textarea":
                _click_force = not visible and ok_layout
                try:
                    el.click(timeout=5000, force=_click_force)
                    # Try simulating real typing first as it's most reliable for Ember state
                    el.press_sequentially(body, delay=15)
                    if (el.input_value(timeout=2000) or "").strip():
                        return True
                except Exception:
                    pass
                if paste_text_into_textarea(el, body):
                    if (el.input_value(timeout=2000) or "").strip():
                        return True
                try:
                    el.click(timeout=5000, force=_click_force)
                    el.fill(body)
                    if (el.input_value(timeout=2000) or "").strip():
                        return True
                except Exception:
                    pass
            else:
                try:
                    el.click(timeout=5000, force=not visible and ok_layout)
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
            visible = loc.is_visible(timeout=2500)
            try:
                ok_layout = bool(loc.evaluate(_layout_visible_js))
            except Exception:
                ok_layout = False
            if not visible and not ok_layout:
                continue
            tag = loc.evaluate("node => node.tagName.toLowerCase()")
            if tag == "textarea":
                try:
                    loc.click(timeout=4000, force=not visible and ok_layout)
                    loc.fill(body)
                    if (loc.input_value(timeout=2000) or "").strip():
                        return True
                except Exception:
                    pass
                if paste_text_into_textarea(loc, body):
                    if (loc.input_value(timeout=2000) or "").strip():
                        return True
            else:
                loc.click(timeout=4000, force=not visible and ok_layout)
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

        # Prevent ProtocolError: No dialog is showing by accepting all dialogs automatically
        page.on("dialog", lambda dialog: dialog.accept())

        _inmail_flow_log(f"step=goto_start profile_url={u!r} timeout_ms={timeout_ms}")

        page.goto(u, wait_until="domcontentloaded", timeout=timeout_ms)
        _inmail_flow_log(f"step=after_goto url={page.url!r}")

        profile_shell_ok = False
        try:
            page.wait_for_selector(
                ", ".join(MESSAGE_BUTTON_SELECTORS[:2]) + ", main h1",
                timeout=min(18000, timeout_ms),
            )
            profile_shell_ok = True
        except Exception as ex:
            _inmail_flow_log(
                "step=profile_shell_wait skipped or failed "
                f"({type(ex).__name__}: {ex}); continuing"
            )

        _inmail_flow_log(
            "step=after_profile_shell_wait "
            f"matched_or_skipped_shell={profile_shell_ok}"
        )

        time.sleep(1.2)
        _inmail_flow_log("step=after_initial_settle_sleep")

        if looks_like_linkedin_auth_wall(page.url):
            _inmail_flow_log("step=STOP auth_wall detected; returning early")
            inner["detail"] = (
                "Stopped at LinkedIn login / checkpoint — use an already-signed-in browser "
                "(--openclaw or --user-data-dir with Sales Nav logged in)."
            )
            return inner

        clicked_msg = False
        clicked_msg_sel: Optional[str] = None
        for sel in MESSAGE_BUTTON_SELECTORS:
            _inmail_flow_log(f"step=message_button_try selector={sel!r}")
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=3000):
                    loc.scroll_into_view_if_needed(timeout=3000)
                    loc.click(timeout=6000)
                    clicked_msg = True
                    clicked_msg_sel = sel
                    break
            except Exception as ex:
                _inmail_flow_log(
                    f"step=message_button_try_failed selector={sel!r} "
                    f"({type(ex).__name__}: {ex})"
                )
                continue

        if not clicked_msg:
            _inmail_flow_log("step=STOP no Message button matched")
            inner["detail"] = (
                "Could not find or click the Message button on this profile. "
                "The profile may not support InMail or the page did not load correctly."
            )
            return inner

        _inmail_flow_log(f"step=message_button_clicked selector={clicked_msg_sel!r}")

        compose_sel = (
            'input[placeholder*="Subject" i], '
            'textarea[aria-label*="draft with AI" i], '
            'textarea[aria-label*="Type your message here or draft with AI" i], '
            'textarea[aria-label*="Type your message" i], '
            'textarea[name="message"][class*="_message-field"], '
            'textarea[name="message"], textarea[class*="_message-field_"], '
            'textarea[id^="compose-form-text-ember"], '
            'div[contenteditable="true"]'
        )
        try:
            page.wait_for_selector(
                compose_sel,
                timeout=min(14000, timeout_ms),
            )
            _inmail_flow_log("step=compose_wait matched composite selector")
        except Exception as ex:
            _inmail_flow_log(
                "step=compose_wait_timeout_or_error "
                f"({type(ex).__name__}: {ex})"
            )
            dump_path = (os.environ.get("LINKEDIN_SN_INMAIL_DEBUG_HTML") or "").strip()
            if dump_path:
                try:
                    with open(dump_path, "w", encoding="utf-8") as fh:
                        fh.write(page.content())
                    _inmail_flow_log(f"wrote page HTML to {dump_path!r}")
                except OSError as ioex:
                    _inmail_flow_log(f"failed to write debug HTML: {ioex}")

        _inmail_flow_log_compose_probe(page, "step=after_compose_wait")
        time.sleep(0.65)
        _inmail_flow_log("step=after_compose_settle_sleep")

        compose = inmail_compose_root(page)
        try:
            nd = page.locator('[role="dialog"]').count()
        except Exception:
            nd = -1
        _inmail_flow_log(
            f"step=compose_root_resolved visible_dialog_count={nd} "
            "(root is a dialog when subject/body live there, else full page)"
        )

        filled_subject = False
        subject_sel_used: Optional[str] = None
        for sel in INMAIL_SUBJECT_SELECTORS:
            _inmail_flow_log(f"step=subject_try selector={sel!r}")
            try:
                subj_el = compose.locator(sel).first
                if subj_el.is_visible(timeout=3000):
                    subj_el.click(timeout=4000)
                    subj_el.fill(subject)
                    time.sleep(0.35)
                    filled_subject = True
                    subject_sel_used = sel
                    break
            except Exception as ex:
                _inmail_flow_log(
                    f"step=subject_try_failed selector={sel!r} "
                    f"({type(ex).__name__}: {ex})"
                )
                continue

        if not filled_subject:
            _inmail_flow_log("step=STOP subject field not found in compose root")
            inner["detail"] = (
                "Message popup opened but could not locate the Subject field. "
                "LinkedIn UI may have changed — update INMAIL_SUBJECT_SELECTORS."
            )
            return inner

        _inmail_flow_log(f"step=subject_filled selector={subject_sel_used!r}")

        _inmail_flow_log("step=body_fill_try compose root")
        filled_body = fill_inmail_body_in_root(compose, body)
        _inmail_flow_log(f"step=body_fill_compose_root ok={filled_body}")
        if not filled_body:
            _inmail_flow_log("step=body_fill_try full page fallback")
            filled_body = fill_inmail_body_in_root(page, body)
            _inmail_flow_log(f"step=body_fill_page_fallback ok={filled_body}")

        if not filled_body:
            _inmail_flow_log("step=STOP body fill failed")
            inner["detail"] = (
                "Subject filled but could not locate or fill the message body field "
                "(InMail textarea). LinkedIn UI may have changed — check INMAIL_BODY_SELECTORS "
                "in linkedin_sales_nav/inmail.py or compose detection (inmail_compose_root)."
            )
            return inner

        if dry_run or not send:
            _inmail_flow_log(
                f"step=early_exit_no_send dry_run={dry_run} send={send}"
            )
            inner["ok"] = True
            inner["detail"] = (
                f"{'dry_run' if dry_run else 'send=False'}: Subject and body filled; "
                "Send was NOT clicked."
            )
            return inner

        time.sleep(0.45)
        _inmail_flow_log("step=before_send_click")
        compose_send = inmail_compose_root(page)
        clicked_send, send_sel_used = click_inmail_send_button(
            compose_send, page, max_wait_s=min(14.0, timeout_ms / 1000.0)
        )

        if not clicked_send:
            _inmail_flow_log("step=STOP send button not clicked")
            inner["detail"] = (
                "Subject and body filled but could not click Send. "
                "The button may still be disabled (try a longer settle delay) or the UI changed."
            )
            return inner

        _inmail_flow_log(f"step=send_clicked via={send_sel_used!r}")

        try:
            page.wait_for_selector(
                'input[placeholder*="Subject" i]',
                state="hidden",
                timeout=8000,
            )
            _inmail_flow_log("step=subject_input_hidden_ok (compose likely closed)")
        except Exception as ex:
            _inmail_flow_log(
                "step=subject_hidden_wait_skipped_or_failed "
                f"({type(ex).__name__}: {ex})"
            )

        _inmail_flow_log("step=done success")
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
