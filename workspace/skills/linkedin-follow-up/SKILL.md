---
name: linkedin-follow-up
description: >-
  Follow up with HubSpot OPEN leads after 48+ hours by sending a second-touch
  LinkedIn Sales Navigator message, then append outreach_conversation and set
  linkedin_follow_up_sent=true in HubSpot without changing outreach_date.
metadata:
  openclaw:
    emoji: 🎯
---

# Lead LinkedIn follow-up (HubSpot `OPEN` → Sales Navigator)

Use the **`hubspot`** skill and **`linkedin-sales-navigator`** skill together: find HubSpot contacts in **`hs_lead_status` = `OPEN`** (already contacted; awaiting engagement per **`lead-outreach`**) whose **`outreach_date`** is **at least 48 hours in the past**, then **follow up in LinkedIn** via their **`linkedin_sales_lead_url`** with a **new** message that references the prior touch without copy-pasting the first outreach. **PATCH** HubSpot by appending **`outreach_conversation`** and setting the follow-up checkbox after each successful send. Do not update **`outreach_date`** in this flow. Do not use public profile URLs to message.

## Step 1 — Fetch contacts ready for a 48h+ follow-up

**Queue definition**

- **`hs_lead_status`** = **`OPEN`** (contacts already messaged; not the fresh **`IN_PROGRESS`** cold-outreach queue from **`lead-outreach`**).
- **`outreach_date`** is **set** and is **earlier** than **now minus 48 hours** (the last touch was at least 48 hours ago). Compute `cutoff = current time (ISO, UTC) − 48 hours` and filter so **`outreach_date` < `cutoff`**.
- **`linkedin_sales_lead_url`**: **required** (Sales Navigator lead page only — same rule as **`skills/lead-outreach/SKILL.md`**).
- **`linkedin_follow_up_sent`** must be **missing** or explicitly **false**.

**HubSpot search (pattern — adjust `crm/objects/.../contacts` path and token to your portal):**

- Combine filters so all eligibility conditions are met: `hs_lead_status` **EQ** `OPEN`, `outreach_date` **LT** `<cutoff_iso>` (e.g. if now is `2026-04-21T12:00:00.000Z`, cutoff is `2026-04-19T12:00:00.000Z`), `linkedin_sales_lead_url` **HAS_PROPERTY**, and **(`linkedin_follow_up_sent` is false OR `linkedin_follow_up_sent` has no value)**.
- Request properties: e.g. `firstname`, `lastname`, `company`, `jobtitle`, `linkedin_sales_lead_url`, `lead_score`, `outreach_conversation`, `outreach_date`, `hs_lead_status`, `hs_content_membership_notes` (or notes fields your portal uses for pathway).
- **Sort** by **`outreach_date` ascending** (oldest last-touch first) if the API allows; otherwise sort client-side so the longest-waiting leads are first.
- **Limit** per run: use a **small bounded batch** (e.g. 5–15) unless the owner specifies otherwise.

**Legacy / edge cases:** If **`outreach_date`** is empty on an `OPEN` contact, do **not** include them in this run — treat as data issue or handle under **`lead-outreach`**, not follow-up. If the search API cannot express the full OR condition for **`linkedin_follow_up_sent`** (missing/false), fetch a constrained `OPEN` batch and filter client-side to keep only records where `outreach_date < cutoff` and `linkedin_follow_up_sent` is missing or false.

Read **`outreach_conversation` in full** so the follow-up does not repeat the same hook or CTA as the last block.

## Step 2 — Open the lead in Sales Navigator

For each selected contact:

1. Open **`linkedin_sales_lead_url`** (Sales Navigator lead page). Do **not** use `linkedin_url` or `hs_linkedin_url` to send.
2. Wait for the page; skim headline/about if needed to keep pathway (**Agency** vs **Business Owner**) aligned with notes.
3. Click the **Message** button on the profile page — the message thread panel opens on screen. If a thread already exists, scroll/read enough of it to see **your prior outbound** so the follow-up is a natural bump, not a duplicate first cold message.

## Step 3 — Compose and send a follow-up LinkedIn Message

**Intent:** One short **second touch** — acknowledge time passed, add **one** new value point or question, stay pathway-aware. **Forbidden:** repeating the first message, generic “just circling back” with no new substance, or more than **~3–4 short sentences**.

**Subject:** Write a short, specific follow-up subject that matches the thread context (for example, `Quick follow-up`).

**Body**

- Nod to prior message **without** long quoting.
- **One** clear next step or question; match **`lead-outreach.md`** / pathway tone where applicable.
- **Draft first:** Write the **whole** message at once in your draft, using **real** line breaks. Do **not** include literal **`\n`**, **`\t`**, etc. in the text you will paste.
- **Paste:** Copy that full body and **paste** it into the Sales Navigator thread **Input body** box (composer) in one go — do not retype line-by-line in the UI.

**Send:** In the open Sales Navigator message thread panel, enter the subject in the subject field, **paste** the full body into **Input body**, click **Send**, and confirm the message appears in the thread.

## Step 4 — Update HubSpot after a successful follow-up

Use **one** send **datetime** (when send succeeded), ISO-8601 with timezone (same as **`lead-outreach`** — full datetime, e.g. **`2026-04-21T10:00:00.000Z`).

**`outreach_conversation`:** **Append** (do not replace). Preserve existing text; add a separator block, e.g. `---`, label **`LinkedIn follow-up`**, same ISO time, and the full subject and body.

**`hs_lead_status`:** Keep **`OPEN`** unless your portal policy moves working leads to another value after a follow-up; default is **leave `OPEN`**.

**`LinkedIn Follow Up Sent` (single checkbox):** Set to **true** after a successful follow-up send.

**Example `PATCH` shape (adjust contact id and strings):**

```
PATCH https://api.hubapi.com/crm/v3/objects/contacts/<contact_id>
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "properties": {
    "hs_lead_status": "OPEN",
    "outreach_conversation": "<existing value>\n\n---\nLinkedIn follow-up sent <ISO datetime>.\nSubject: <subject>\nBody: <full body>",
    "linkedin_follow_up_sent": "true"
  }
}
```

Use your portal's exact internal property name for **`LinkedIn Follow Up Sent`** if it differs from `linkedin_follow_up_sent`.

If send **fails**, log the reason, **do not** PATCH as if sent, continue with the next lead.

## Step 5 — Close tabs and report

1. Close LinkedIn tabs opened for the run.
2. Summary table:

| Lead | Company | Last `outreach_date` (before run) | Hours since last touch | Follow-up sent | `hs_lead_status` | `LinkedIn Follow Up Sent` |
|------|---------|-----------------------------------|------------------------|---------------|------------------|-------------------------|

If HubSpot or the browser cannot be used reliably, **do not** fabricate send confirmations or patch rows.

## What this prompt is *not*

- **Not** primary cold outreach from the **`IN_PROGRESS`** queue — use **`skills/lead-outreach/SKILL.md`** and **`hs_lead_status` = `IN_PROGRESS`**.
- **Not** inbound **Sales Navigator inbox replies** — use **`skills/lead-conversation/SKILL.md`**.
