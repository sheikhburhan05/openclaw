---
name: linkedin-messenger
description: >-
  Standalone Playwright script to send a LinkedIn message from a profile URL (optional credentials or manual login).
  Prefer skill `linkedin-message-browser` when using OpenClaw's built-in browser tool inside the agent. Use this skill when the user
  wants the Python/Chromium script path, --dry-run, or explicit CLI automation outside the gateway browser.
---

# LinkedIn Messenger (standalone Playwright)

**OpenClaw agent + `browser` tool**: use **`linkedin-message-browser`** (`skills/linkedin-message-browser/SKILL.md`) — pass **profile URL + message**; the agent drives **`profile="openclaw"`** per [Browser](https://docs.openclaw.ai/tools/browser).

This skill is the **alternate** path: a **separate** Chromium via **Playwright** script (not the gateway-managed browser).

Automate sending a LinkedIn message to a profile URL using a real Chromium browser.

## Requirements

- Python 3: `python3`
- Playwright: `pip3 install playwright && python3 -m playwright install chromium`
- Script: `scripts/linkedin_message.py` (in this skill directory)

## Workflow

1. **Collect inputs** from the user:
   - `--profile-url` — the `linkedin.com/in/...` URL (required)
   - `--message` — the message text to send (required)
   - `--email` / `--password` — LinkedIn credentials (optional; if omitted, user logs in manually)
   - `--dry-run` — type the message but don't click Send (good for review)

2. **Run the script** (headed mode by default so user can see what's happening):

```bash
python3 <skill-dir>/scripts/linkedin_message.py \
  --profile-url "https://www.linkedin.com/in/TARGET" \
  --message "Your message here"
```

With credentials (auto-login):
```bash
python3 <skill-dir>/scripts/linkedin_message.py \
  --profile-url "https://www.linkedin.com/in/TARGET" \
  --message "Your message here" \
  --email "you@email.com" \
  --password "yourpassword"
```

Dry run (compose but don't send):
```bash
python3 <skill-dir>/scripts/linkedin_message.py \
  --profile-url "https://www.linkedin.com/in/TARGET" \
  --message "Your message here" \
  --dry-run
```

## Important Notes

- **Browser opens visibly** by default so the user can handle 2FA/CAPTCHA challenges.
- If no credentials are given, the script waits up to **120 seconds** for manual login.
- The **Message button** only appears if the two accounts are connected (1st degree) or the target allows InMail / Open Profiles. If the button isn't found, the script reports why.
- **LinkedIn ToS**: Automated messaging is against LinkedIn's Terms of Service. Use responsibly — low volume, personalized messages, real connections only. Heavy use risks account restriction.
- Resolve the skill directory path at runtime; it is typically `~/.openclaw/workspace/skills/linkedin-messenger`.
