---
name: lead-outreach
description: >-
  Run LinkedIn outreach only: read remaining Sales Navigator InMail credits, cap sends using
  remaining weekdays this month (Mon-Fri), search HubSpot for IN_PROGRESS contacts with lead_score and
  linkedin_sales_lead_url, sort by lead_score descending, open each Sales Navigator lead page
  (linkedin_sales_lead_url only - no public profile URLs for messaging), send a LinkedIn Message
  (subject + body), PATCH hs_lead_status, outreach_date (HubSpot datetime, full date+time of send),
  and outreach_conversation (append sent copy), and report. First-touch messaging follows
  workspace/skills/messaging-guidelines/SKILL.md. Use when the user wants to message
  qualified leads, run LinkedIn outreach, or work the post-qualification queue. Requires hubspot
  and linkedin-sales-navigator (browser); Sales Navigator session required.

metadata:
  openclaw:
    emoji: 💬
---

Use the `hubspot` skill and `linkedin-sales-navigator` skill together to **outreach only**: **pace by InMail credits** (working days left in the month), load contacts already qualified and queued, open their Sales Navigator profile, send a **LinkedIn Message** (subject + body), then update HubSpot.

## Step 0 — InMail credits and daily send cap (working days only)

**Before** fetching HubSpot contacts or opening lead tabs:

1. **Read remaining InMail credits** in Sales Navigator (browser): open Sales Navigator (`linkedin-sales-navigator` skill), **snapshot** the chrome where LinkedIn surfaces monthly InMail allowance (often near compose / account or messaging entry points — wording like "InMail credits" or "credits remaining"). Record the integer **credits remaining**.
2. **Compute today's send budget** using **weekdays only** (Monday-Friday): count each weekday from **today** through the **last day of the current calendar month** (inclusive). Divide **`credits_remaining // working_days_remaining`** (integer division). That is the **maximum messages to send this run** (cap HubSpot fetch + sends at this number). **Re-run this step each session** with fresh credits so the budget tracks the rest of the month.

**Python helper** (stdlib only): [`scripts/inmail_monthly_pacing.py`](scripts/inmail_monthly_pacing.py)

- Import: `inmail_pacing_plan`, `working_days_remaining_in_month` — or run CLI:

```bash
python3 workspace/skills/lead-outreach/scripts/inmail_monthly_pacing.py --credits <N>
```

- Optional: `--date YYYY-MM-DD` to simulate another "today"; `--min-one` if `credits > 0` but floor division yields 0 (forces 1 send — may burn credits faster).

Use **`plan.sends_budget_today`** as the cap. Do **not** exceed it unless the human overrides (e.g. month-end catch-up).

---

## Step 1 — Fetch leads ready for outreach (IN_PROGRESS, highest `lead_score` first)

Search contacts with **`hs_lead_status = IN_PROGRESS`** (set by qualification when score >= 40), **`lead_score` populated** (from qualification), and **`linkedin_sales_lead_url`** (Sales Navigator lead page — **required** for this workflow; do not use `linkedin_url` or `hs_linkedin_url` to open or message). Sort by **`lead_score` descending** so the highest-scored leads are messaged first.

Use a **single** `filterGroup` (all filters AND): status, score, and Sales Navigator lead URL:

```
POST https://api.hubapi.com/crm/objects/2026-03/contacts/search
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "filterGroups": [
    {
      "filters": [
        {
          "propertyName": "hs_lead_status",
          "operator": "EQ",
          "value": "IN_PROGRESS"
        },
        {
          "propertyName": "lead_score",
          "operator": "HAS_PROPERTY"
        },
        {
          "propertyName": "linkedin_sales_lead_url",
          "operator": "HAS_PROPERTY"
        }
      ]
    }
  ],
  "properties": [
    "firstname",
    "lastname",
    "company",
    "jobtitle",
    "linkedin_sales_lead_url",
    "lead_score",
    "outreach_conversation",
    "outreach_date",
    "hs_lead_status"
  ],
  "sorts": [
    {
      "propertyName": "lead_score",
      "direction": "DESCENDING"
    }
  ],
  "limit": 5,
  "after": "0"
}
```

Set **`limit`** to **`sends_budget_today`** from Step 0 (example above uses `5` only as shape). Do not fetch more contacts than you will message this run.

**Sort:** Use descending **`lead_score`** first with the object-form sort shown above. If your HubSpot API rejects that sort shape, fetch the batch without a server sort and **re-order results client-side** so the highest numeric **`lead_score`** is messaged first.

**Legacy rows:** If some `IN_PROGRESS` contacts lack **`lead_score`** (not yet backfilled), remove the **`lead_score` HAS_PROPERTY** filter, fetch a larger batch if needed, and **sort client-side** by numeric **`lead_score`** descending (treat empty as last). Contacts **without** **`linkedin_sales_lead_url`** are **out of scope** for this prompt — backfill that URL via lead sourcing / qualification before outreach.

Read **`outreach_conversation`** when present so appended outreach entries stay after prior thread history and you avoid repeating the same angle. Read **`outreach_date`** when present for last-touch context (you will overwrite it after a successful send with this run's send **datetime**).

---

## Step 2 — Open each lead's LinkedIn Sales Navigator profile

For each contact:

1. Open **`linkedin_sales_lead_url`** in a new tab (Sales Navigator lead page — **only** URL used for **Message** in this workflow). Do **not** open `linkedin_url` or `hs_linkedin_url` for sending.
2. Wait for the profile to load.
3. Skim headline, about, recent activity to infer **industry / vertical** and **pathway** (agency vs business owner) — enough to pick the right opening question, not a full brief.

---

## Step 3 — Write and send a LinkedIn Message (not connection-only)

**Before composing:** read `workspace/skills/messaging-guidelines/SKILL.md` and follow it in full. All tone, style, industry openers, body rules, and conversation guidelines live there.

Key constraints for this step:

- This is a **first touch** — never pitch, never mention AI, never ask for a call.
- Open with **`Hey {name},`** or **`Hi {name},`** and one short operational question matched to their vertical.
- Subject line: under ~10 words, plain operational curiosity specific to their niche.
- Body: 2-4 short sentences maximum; no filler, no bullet markers, no `\n` escape sequences in the sent text.
- Draft the full message first, then paste into the Sales Navigator composer in one go — do not type line by line.
- HubSpot `outreach_conversation` append blocks (Step 4) may use `---` as a log separator — that is internal only, never goes in the LinkedIn message itself.

**Send steps (match Sales Navigator UI)**

1. On the profile, click **Message**.
2. In the compose panel, fill **Subject (required)**.
3. Fill the **message body**.
4. Click **Send**.
5. Confirm send; then close the profile tab.

**Body shape**

```text
Hey {name},

<one operational question for their vertical — short, casual, no pitch>
```

---

## Step 4 — Update HubSpot after send

Pick one **send datetime** (the moment the message was confirmed sent) and reuse it everywhere below. **`outreach_date`** is a HubSpot **datetime** field: PATCH it with **date and time**, not a date-only string. Use ISO-8601 with timezone, e.g. **`2026-04-20T18:05:00.000Z`** (UTC `Z`) or **`2026-04-20T14:05:00-04:00`** — include hours, minutes, seconds (and milliseconds if your client sends them); stay consistent (e.g. always UTC).

**`outreach_date`:** Set to that same send datetime (replaces any prior value — it means "last outreach at").

**`outreach_conversation`:** Append each sent message (do not replace the whole field). Use the existing value from Step 1 (or empty string if unset), then add a separator block with the **same** send timestamp, subject, and full body, e.g. `\n\n---\nLinkedIn message sent <ISO datetime>.\nSubject: <subject>\nBody: <full body>`.

```
PATCH https://api.hubapi.com/crm/v3/objects/contacts/<contact_id>
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "properties": {
    "hs_lead_status": "OPEN",
    "outreach_date": "<same ISO-8601 send datetime as in conversation block, e.g. 2026-04-20T18:05:00.000Z>",
    "outreach_conversation": "<existing outreach_conversation or empty>\n\n---\nLinkedIn message sent <ISO datetime>.\nSubject: <subject>\nBody: <full body>"
  }
}
```

Use **`OPEN`** (or your portal's "Contacted / Working" value) instead of `IN_PROGRESS` so this contact is not picked again on the next outreach search. If you prefer to keep `IN_PROGRESS` until a reply, document that in your portal and change the filter in Step 1 accordingly.

---

## Step 5 — Close tabs and report

1. Close all LinkedIn tabs opened for this run.
2. Summary table:

| Lead | Company | Score (`lead_score`) | Industry (inferred) | Pathway (inferred) | Sent | `outreach_date` | HubSpot updated |
|------|---------|----------------------|----------------------|----------------------|------|-----------------|---------------|

If send fails (limits, already in thread, UI blocked), log the reason, skip PATCH status to "sent" if appropriate, and continue.
