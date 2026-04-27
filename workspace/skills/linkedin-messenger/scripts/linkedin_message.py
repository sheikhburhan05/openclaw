#!/usr/bin/env python3
"""
LinkedIn Messenger - Opens browser, logs into LinkedIn, navigates to a profile,
and sends a message using Playwright (headed mode so the user can handle 2FA).

Usage:
    python3 linkedin_message.py --profile-url <URL> --message "<text>"
                                [--email <email>] [--password <password>]
                                [--headless]

If --email/--password are omitted, the script pauses for the user to log in manually.
"""

import argparse
import sys
import time

def main():
    parser = argparse.ArgumentParser(description="Send a LinkedIn message via browser automation")
    parser.add_argument("--profile-url", required=True, help="LinkedIn profile URL, e.g. https://linkedin.com/in/johndoe")
    parser.add_argument("--message", required=True, help="Message text to send")
    parser.add_argument("--email", default="", help="LinkedIn email (optional; skip for manual login)")
    parser.add_argument("--password", default="", help="LinkedIn password (optional; skip for manual login)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (requires credentials)")
    parser.add_argument("--dry-run", action="store_true", help="Navigate but do not click Send")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    except ImportError:
        print("[ERROR] Playwright not installed. Run: pip3 install playwright && python3 -m playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless, slow_mo=50)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── LOGIN ────────────────────────────────────────────────────────────────
        print("[*] Opening LinkedIn...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        if args.email and args.password:
            print("[*] Logging in with provided credentials...")
            page.fill("#username", args.email)
            page.fill("#password", args.password)
            page.click("button[type='submit']")
            try:
                page.wait_for_url("**/feed/**", timeout=15000)
                print("[+] Logged in.")
            except PwTimeout:
                print("[!] Login may have required 2FA or CAPTCHA. Waiting 60s for manual completion...")
                page.wait_for_url("**/feed/**", timeout=60000)
        else:
            print("[*] No credentials provided. Please log in manually in the browser window.")
            print("[*] Waiting up to 120 seconds for you to log in...")
            try:
                page.wait_for_url("**/feed/**", timeout=120000)
                print("[+] Logged in.")
            except PwTimeout:
                print("[ERROR] Login timeout. Please try again.")
                browser.close()
                sys.exit(1)

        # ── NAVIGATE TO PROFILE ───────────────────────────────────────────────
        profile_url = args.profile_url.rstrip("/")
        print(f"[*] Navigating to profile: {profile_url}")
        page.goto(profile_url, wait_until="domcontentloaded")
        time.sleep(2)

        # ── CLICK MESSAGE BUTTON ──────────────────────────────────────────────
        print("[*] Looking for Message button...")
        msg_selectors = [
            "button:has-text('Message')",
            "a:has-text('Message')",
            "[aria-label*='message' i]",
            ".pvs-profile-actions button:has-text('Message')",
        ]
        clicked = False
        for sel in msg_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    clicked = True
                    print(f"[+] Clicked Message button (selector: {sel})")
                    break
            except Exception:
                continue

        if not clicked:
            print("[!] Could not find Message button automatically.")
            print("[!] The profile may not allow direct messages, or you're not connected.")
            print("[!] Browser will stay open for 30s so you can inspect manually.")
            time.sleep(30)
            browser.close()
            sys.exit(1)

        # ── TYPE MESSAGE ──────────────────────────────────────────────────────
        time.sleep(2)
        print("[*] Typing message...")
        msg_box_selectors = [
            ".msg-form__contenteditable",
            "[contenteditable='true']",
            "div[role='textbox']",
            "textarea",
        ]
        typed = False
        for sel in msg_box_selectors:
            try:
                box = page.locator(sel).first
                if box.is_visible(timeout=3000):
                    box.click()
                    box.type(args.message, delay=30)
                    typed = True
                    print(f"[+] Message typed.")
                    break
            except Exception:
                continue

        if not typed:
            print("[ERROR] Could not find message input box.")
            time.sleep(30)
            browser.close()
            sys.exit(1)

        # ── SEND ──────────────────────────────────────────────────────────────
        if args.dry_run:
            print("[DRY RUN] Message composed but NOT sent. Browser will stay open for 30s.")
            time.sleep(30)
        else:
            time.sleep(1)
            send_selectors = [
                "button.msg-form__send-button",
                "button[type='submit']:has-text('Send')",
                "button:has-text('Send')",
                "[aria-label='Send']",
            ]
            sent = False
            for sel in send_selectors:
                try:
                    send_btn = page.locator(sel).first
                    if send_btn.is_visible(timeout=3000):
                        send_btn.click()
                        sent = True
                        print(f"[+] Message sent!")
                        break
                except Exception:
                    continue

            if not sent:
                print("[!] Could not find Send button. Message is typed but NOT sent.")
                print("[!] Browser staying open for 30s so you can send manually.")
                time.sleep(30)
            else:
                time.sleep(2)

        browser.close()
        print("[*] Done.")

if __name__ == "__main__":
    main()
