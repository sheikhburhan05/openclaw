---
name: linkedin-message-browser
description: >-
  Send a LinkedIn direct message when the user provides a profile URL and message text, using the OpenClaw browser tool
  (navigate → snapshot → act). Use for "message this LinkedIn URL", "DM them on LinkedIn", or paste linkedin.com/in/... plus copy.
  Requires an active LinkedIn session in the openclaw browser; manual login per browser-login docs. Confirm exact message before Send.
metadata:
  openclaw:
    emoji: ✉️
---

# LinkedIn message (OpenClaw browser tool)

Send a **LinkedIn DM** by driving the **managed `openclaw` browser** through the **`browser` tool** — not a separate Playwright script or ad-hoc Chrome profile.

**Docs**: [Browser](https://docs.openclaw.ai/tools/browser) · [Browser login](https://docs.openclaw.ai/tools/browser-login)

## Inputs (from the user)

| Input | Required | Notes |
|--------|----------|--------|
| **Profile URL** | Yes | `https://www.linkedin.com/in/...` (normalize trailing slash) |
| **Message body** | Yes | Exact text to send — **read it back and get approval** before Send |
| **Dry run** | Optional | User asks to compose only: type message, **do not** click Send |

Do **not** ask for or accept LinkedIn passwords in chat; login happens **in the browser window**.

## Preconditions

1. **Gateway browser** enabled and Playwright-capable paths available for snapshot/act (see [Browser](https://docs.openclaw.ai/tools/browser)).
2. **LinkedIn session**: User is logged in on the **`openclaw`** profile (one-time manual login). If logged out, open LinkedIn login and wait for the user to complete it (2FA/CAPTCHA in-browser).
3. **Messaging availability**: The **Message** control appears only for **1st-degree connections**, **InMail**, or **Open Profile** / similar — if it is missing, stop and explain; do not spam Connect to bypass.

## Agent workflow

1. **Start / ensure browser** (if needed): use `browser` **status** or CLI:
   ```bash
   openclaw browser --browser-profile openclaw status
   openclaw browser --browser-profile openclaw start
   ```
2. **Target profile**: `browser` **navigate** or **open** the given profile URL with **`profile="openclaw"`**.
3. **Snapshot** the page; locate the primary **Message** action (button or link) by ref from the snapshot.
4. **Act**: **click** the Message ref → wait for compose UI → **snapshot** again.
5. **Type** the approved message into the composer ref(s) from the latest snapshot.
6. **Send**:
   - If **dry run**: stop after typing; tell the user it was not sent.
   - Otherwise: **click** Send only after **explicit user confirmation** of the exact text.
7. If navigation or clicks fail: **re-snapshot** (refs are not stable across steps); avoid rapid-fire actions.

If the agent runs in a **sandbox** and LinkedIn blocks or the tool defaults to the wrong target, follow [Browser](https://docs.openclaw.ai/tools/browser) for **host** browser access (`allowHostControl`, `target`) when the user is at the machine.

## CLI (optional human check)

```bash
openclaw browser --browser-profile openclaw open "https://www.linkedin.com/in/USERNAME/"
openclaw browser --browser-profile openclaw snapshot
```

## Safety

- **Never send** without the user’s **explicit OK** on the final message body.
- **LinkedIn ToS**: Automated or scripted messaging can violate terms; keep volume **low**, messages **personal**, use only for legitimate outreach the user requested.
- **Rate**: Do not chain many sends in one session; space actions like other LinkedIn skills (~30 actions/hour guideline).

## Related

- Workspace **`linkedin`** skill: general LinkedIn browser patterns and safety.
- **`linkedin-messenger`** skill: optional **standalone Playwright script** if the user prefers a separate Chromium process — prefer **this** skill when using the **OpenClaw `browser` tool** inside the agent.
