---
name: connection-outreach
description: >-
  Post-connection LinkedIn outreach only: search HubSpot for IN_PROGRESS contacts with lead_score and
  linkedin_sales_lead_url, open each Sales Navigator lead page, verify they accepted the connection
  (1st-degree / connected - not InMail), send a LinkedIn Message (subject + body) without using InMail
  credits, then PATCH hs_lead_status, outreach_date, outreach_conversation (append), and is_connected=true.
  First-touch messaging follows workspace/skills/messaging-guidelines/SKILL.md.
  Use when the user wants to message leads only after connection acceptance or avoid InMail spend.
  Requires hubspot and linkedin-sales-navigator (browser); Sales Navigator session required.

metadata:
  openclaw:
    emoji: 🤝
---

Use the **`hubspot`** skill and **`linkedin-sales-navigator`** skill together for **connection-based outreach**: load contacts already qualified and queued (**`IN_PROGRESS`** with score and Sales Navigator lead URL), confirm on their Sales Navigator profile that **they accepted your connection**, send a **LinkedIn Message** through the **free 1st-degree thread** (**no InMail credits**), then update HubSpot including **`is_connected`** = **`true`**.

This workflow **never** sends **InMail**. If the lead is **not** connected yet, **skip** messaging and **do not** set **`is_connected`** true.

## Prerequisites — HubSpot property

Ensure contacts have a HubSpot contact property **`is_connected`** (boolean / single checkbox). Create it in HubSpot if missing so PATCH accepts **`"true"`** / **`"false"`** string values like other checkbox fields.

## Step 0 — Batch size (no InMail pacing)

There is **no** InMail credit budget step here — capacity is whatever LinkedIn allows on normal threads. Use a **small bounded batch** per run (e.g. **5-15** contacts) unless the human specifies otherwise.

- When searching, request **`is_connected`** in **`properties`**.
- After fetch, **skip** rows where **`is_connected`** is already **`true`** (already synced).

Set **`limit`** in Step 1 to that batch cap.

---

## Step 1 — Fetch leads ready for outreach (`IN_PROGRESS`, highest `lead_score` first)

Search contacts with **`hs_lead_status = IN_PROGRESS`** (set by qualification when score >= 40), **`lead_score` populated** (from qualification), and **`linkedin_sales_lead_url`** (Sales Navigator lead page — **required** for this workflow; do not use `linkedin_url` or `hs_linkedin_url` to open or message). Sort by **`lead_score` descending** so the highest-scored leads are handled first.

Use a **single** `filterGroup` (all filters AND): status, score, and Sales Navigator lead URL. Include **`is_connected`** in **`properties`** returned so you can skip contacts already marked connected client-side.

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
    "hs_lead_status",
    "is_connected",
    "outreach_account"
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

Set **`limit`** to your Step 0 batch cap (example uses **`5`** only as shape). Do not fetch more contacts than you will process this run.

**Sort:** Use descending **`lead_score`** first with the object-form sort shown above. If your HubSpot API rejects that sort shape, fetch the batch without a server sort and **re-order results client-side** so the highest numeric **`lead_score`** is handled first.

**Legacy rows:** If some `IN_PROGRESS` contacts lack **`lead_score`** (not yet backfilled), remove the **`lead_score` HAS_PROPERTY** filter, fetch a larger batch if needed, and **sort client-side** by numeric **`lead_score`** descending (treat empty as last). Contacts **without** **`linkedin_sales_lead_url`** are **out of scope** for this workflow — backfill that URL via lead sourcing / qualification before outreach.

Read **`outreach_conversation`** when present so appended outreach entries stay after prior thread history and you avoid repeating the same angle. Read **`outreach_date`** when present for last-touch context (you will overwrite it after a successful send with this run's send **datetime**).

---

## Step 2 — Open each lead's Sales Navigator profile, verify connection, then skim for messaging

**Browser profile routing:** Before opening any tabs, read **`outreach_account`** from the contact's HubSpot record and use that as the browser profile (`openclaw browser --browser-profile <outreach_account>`). If **`outreach_account`** is missing or empty, default to **`openclaw`**. All tabs opened for this lead must use that same profile's browser session.

For each contact (**after** skipping **`is_connected`** already **`true`**):

1. Open **`linkedin_sales_lead_url`** in a new tab (Sales Navigator lead page — **only** URL used for **Message** in this workflow). Do **not** open `linkedin_url` or `hs_linkedin_url` for sending.
2. Wait for the profile to load; **snapshot** or read the visible chrome.

**Verification — treat as "connected / accepted" only if** the UI clearly indicates **1st-degree** (or equivalent **Connected** / **1st** relationship badge on Sales Navigator / lead sidebar) **and** you can open a **standard message thread** that does **not** require consuming **InMail** (no **InMail** send path as the **only** option).

**Verification — treat as "not connected yet" if** you see **Pending invitation**, **Connect** as the primary action, **2nd** / **3rd+** only without a free **Message** path, or only **InMail**.

- If status is **Pending** (invitation already sent) — skip messaging; leave `hs_lead_status` unchanged; log "pending — awaiting acceptance" and continue to the next lead.
- If status is **not connected and no invite sent** (Connect is the primary action) — send a connection request now using the same `outreach_account` browser profile, then skip messaging for this run:

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --browser-profile <outreach_account or openclaw if not set> \
  --action connect \
  --profile-url '<linkedin_sales_lead_url>'
```

After sending the request, log "connection request sent" and continue to the next lead. Do **not** PATCH `is_connected` true; leave `hs_lead_status` unchanged.

3. If connected, skim headline, about, recent activity to infer **industry / vertical** and **pathway** (agency vs business owner) — enough to pick the right opening question.

---

## Step 3 — Write and send a LinkedIn Message (connected thread, not InMail)

**Before composing:** read `workspace/skills/messaging-guidelines/SKILL.md` and follow it in full. All tone, style, industry openers, body rules, and conversation guidelines live there.

Key constraints for this step:

- This is a **first touch** — never pitch, never mention AI, never ask for a call.
- Open with **`Hey {name},`** or **`Hi {name},`** and one short operational question matched to their vertical.
- Subject line: under ~10 words, plain operational curiosity specific to their niche.
- Body: 2-4 short sentences maximum; no filler, no bullet markers, no `\n` escape sequences in the sent text.
- Draft the full message first, then paste into the composer in one go — do not type line by line.
- HubSpot `outreach_conversation` append blocks (Step 4) may use `---` as a log separator — that is internal only, never goes in the LinkedIn message itself.

Use only the **regular message thread** for **connected** leads — **not** an **InMail-only** flow.

**Send steps (match Sales Navigator UI)**

1. On the profile, click **Message**.
2. In the compose panel, fill **Subject (required)** when the UI shows a subject field; otherwise compose body only per current UI.
3. Fill the **message body**.
4. Click **Send**.
5. Confirm send; then close the profile tab.

**Body shape**

```text
Hey {name},

<one operational question for their vertical — short, casual, no pitch>
```

If send fails (limits, already in thread, UI blocked), log the reason; **do not** PATCH **`is_connected`** or status to imply success unless policy says otherwise, and continue.

---

## Step 4 — Update HubSpot after successful connected send

Pick one **send datetime** (the moment the message was confirmed sent) and reuse it everywhere below. **`outreach_date`** is a HubSpot **datetime** field: PATCH it with **date and time**, not a date-only string. Use ISO-8601 with timezone, e.g. **`2026-04-20T18:05:00.000Z`** (UTC `Z`) or **`2026-04-20T14:05:00-04:00`** — include hours, minutes, seconds (and milliseconds if your client sends them); stay consistent (e.g. always UTC).

**`is_connected`:** Set to **`true`** (string **`"true"`** for checkbox properties).

**`outreach_date`:** Set to that same send datetime (replaces any prior value — it means "last outreach at").

**`outreach_conversation`:** Append each sent message (do not replace the whole field). Use the existing value from Step 1 (or empty string if unset), then add a separator block with the **same** send timestamp, subject, and full body, e.g. `\n\n---\nLinkedIn message sent <ISO datetime>.\nSubject: <subject>\nBody: <full body>`. Omit the **`Subject:`** line in the append block if the UI had no subject field.

**`hs_lead_status`:** Set to **`OPEN`** (or your portal's "Contacted / Working" value) instead of **`IN_PROGRESS`** so this contact is not picked again on the next **`IN_PROGRESS`** outreach search.

```
PATCH https://api.hubapi.com/crm/v3/objects/contacts/<contact_id>
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "properties": {
    "hs_lead_status": "OPEN",
    "is_connected": "true",
    "outreach_date": "<same ISO-8601 send datetime as in conversation block, e.g. 2026-04-20T18:05:00.000Z>",
    "outreach_conversation": "<existing outreach_conversation or empty>\n\n---\nLinkedIn message sent <ISO datetime>.\nSubject: <subject>\nBody: <full body>"
  }
}
```

If you prefer to keep **`IN_PROGRESS`** until a reply, document that in your portal and change the filter in Step 1 accordingly.

---

## Step 5 — Close tabs and report

1. Close all LinkedIn tabs opened for this run.
2. Summary table:

| Lead | Company | Score (`lead_score`) | Connected (verified) | Action taken | `outreach_date` | `is_connected` | HubSpot updated |
|------|---------|----------------------|----------------------|--------------|-----------------|----------------|-----------------|

Possible values for **Action taken**: `Message sent` / `Connection request sent (awaiting acceptance)` / `Pending — skipped`.
