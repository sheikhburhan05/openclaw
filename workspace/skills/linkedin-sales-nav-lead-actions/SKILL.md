---
name: linkedin-sales-nav-lead-actions
description: >-
  Python Playwright automation on LinkedIn Sales Navigator `/sales/lead/` profile URLs: **connect**
  (overflow → Connect), **InMail** (Message → subject + body), or **save lead to list**. Prefer
  `--openclaw` / CDP (`openclaw browser --browser-profile openclaw`); optional standalone Chromium
  with a logged-in profile; no credential automation. Use when the user mentions Sales Nav lead
  actions, connect requests, InMail, save to list, or scripted profile outreach.
  **Alias (old id):** `linkedin-sales-nav-connect` (folder was renamed).
homepage: https://www.linkedin.com/sales
metadata:
  openclaw:
    emoji: 📩
---

# LinkedIn Sales Navigator — Lead profile actions (Playwright)

## Why this exists

Encoding **stable selectors** in [`scripts/linkedin_sales_nav/inmail.py`](scripts/linkedin_sales_nav/inmail.py) (`INMAIL_BODY_SELECTORS`), [`scripts/linkedin_sales_nav/connect_actions.py`](scripts/linkedin_sales_nav/connect_actions.py), and [`scripts/linkedin_sales_nav/save.py`](scripts/linkedin_sales_nav/save.py) beats brittle discovery each run.

**Do not rely on brittle `div#…` IDs** — prefer compound `textarea[name="message"][class*="_message-field--with-subject_"]`, **`aria-label` containing “Type your message here or draft with AI”**, `id^="compose-form-text-ember"`, `_message-field_*` class stubs, roles, overflow triggers, and literal **Connect** / **Message** / **Send** text.

CLI entry: [`scripts/linkedin_sales_nav_cli.py`](linkedin_sales_nav_cli.py). Optional legacy alias: [`scripts/sales_nav_connect.py`](sales_nav_connect.py) (thin forwarder to the same CLI).

Typical UX:

| Action | Flow |
|--------|------|
| **connect** | **⋯** overflow next to Message → **Connect** → invite modal (**Send** / Send without note) |
| **inmail** | **Message** → Subject → body (`textarea` Ember composer; label often **…or draft with AI**) → **Send** |
| **save** | **Save / Saved** on lead → choose list (**`--list-name`**) |

## Requirements

```bash
pip3 install playwright && python3 -m playwright install chromium
```

Script: `workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py`.

Assumes Sales Navigator is **already signed in** (**no credential automation**).

## OpenClaw browser profile (**recommended**)

Reuse the gateway Chrome session via **CDP** — see **`cdpUrl`** (`openclaw browser --browser-profile openclaw status`; often **`http://127.0.0.1:18800`**).

```bash
openclaw browser --browser-profile openclaw status
openclaw browser --browser-profile openclaw start   # if needed

python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action connect \
  --profile-url 'https://www.linkedin.com/sales/lead/REPLACE,...'
```

Override with **`OPENCLAW_BROWSER_CDP_URL`** or **`--cdp-url`**. Opens a **new tab** for automation, then closes it.

**Docs:** [Browser tool](https://docs.openclaw.ai/tools/browser) · workspace **`TOOLS.md`**.

## CLI — `--action`

| Value | Requires | Purpose |
|-------|----------|---------|
| `connect` (default) | optional `--note` | Connection invite |
| `inmail` | **`--subject`**, **`--body`** | InMail composer + Send |
| `save` | optional `--list-name` (default: `Agent's Lead List`) | Add lead to a list |

Shared: **`--profile-url`**, **`--openclaw`** / **`--cdp-url`**, **`--user-data-dir`** (mutually exclusive with CDP).

**Connection (OpenClaw):**

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action connect \
  --profile-url 'https://www.linkedin.com/sales/lead/REPLACE_ME' \
  --note "Optional invitation note."
```

**InMail (OpenClaw):**

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action inmail \
  --profile-url 'https://www.linkedin.com/sales/lead/REPLACE_ME' \
  --subject "Quick question" \
  --body $'Hello,\n\n…'
```

- **`--no-send`** — fill subject/body only; **do not** click Send (preview/edit in browser).
- **`--dry-run`** — also skips Send where applicable.

**Save to list:**

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action save \
  --profile-url 'https://www.linkedin.com/sales/lead/REPLACE_ME' \
  --list-name "Agent's Lead List"
```

Standalone Chromium (**not** `--openclaw`): use **`--user-data-dir`** or a temporary profile; you must already be logged into Sales Nav in that profile — same pattern as Connect.

## Callable API

```python
from linkedin_sales_nav import (
    send_sales_nav_connection_request,
    send_inmail_message,
    save_lead_to_list,
)
# or: ``from linkedin_sales_nav_cli import main`` to call the same argparse entry from code

send_sales_nav_connection_request(
    "https://www.linkedin.com/sales/lead/…",
    use_openclaw_browser=True,
    cdp_url=None,
    note="Optional connect note",
    dry_run=False,
)

send_inmail_message(
    "https://www.linkedin.com/sales/lead/…",
    subject="Subject line",
    body="InMail body",
    use_openclaw_browser=True,
    send=True,
    dry_run=False,
)

save_lead_to_list(
    "https://www.linkedin.com/sales/lead/…",
    list_name="Agent's Lead List",
    use_openclaw_browser=True,
    dry_run=False,
)
```

All return **`{"ok": bool, "detail": str, "profile_url": str}`** (exact keys stable in code).

## OpenClaw `browser` tool vs this script

- **Interactive `browser` tool** (`linkedin-sales-navigator`, `linkedin-message-browser`): snapshot → refs; best when the agent drives the UI live.
- **This script**: fixed Playwright flow; **`--openclaw`** uses the **same** session for repeatable **`connect` / `inmail` / `save`** from cron or wrapping scripts.

## Safety

- **LinkedIn Terms of Use**: bulk automation risks restrictions.
- Prefer low volume and human-approved copy; **`--no-send`** / **`--dry-run`** before going live.

## Related

- `linkedin-sales-navigator` — filter/search via OpenClaw browser.
- `linkedin-messenger` — standard `linkedin.com/in/...` standalone Playwright DMs.
