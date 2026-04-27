# Email follow-up (HubSpot `OPEN` + LinkedIn follow-up done -> Instantly, 72h+)

Use the **`hubspot`** skill and **`instantly-email`** skill together: find HubSpot contacts in **`hs_lead_status` = `OPEN`** where **`linkedin_follow_up_sent`** is **true** and **`outreach_date`** is **at least 72 hours in the past**, then send a **new follow-up email** via Instantly that references the prior touch without copy-pasting the first outreach. After each successful send, **PATCH** HubSpot by appending **`outreach_conversation`** and setting **`email_follow_up_sent`** to **true**. Do not update **`outreach_date`** in this flow.

## Step 1 - Fetch contacts ready for a 72h+ follow-up

**Queue definition**

- **`hs_lead_status`** = **`OPEN`**.
- **`linkedin_follow_up_sent`** = **true**.
- **`outreach_date`** is **set** and is **earlier** than **now minus 72 hours**. Compute `cutoff = current time (ISO, UTC) - 72 hours` and filter so **`outreach_date` < `cutoff`**.
- **Email address required**: `email` must exist and be valid.
- **`email_follow_up_sent`** should be **missing** or **false** to avoid duplicate email follow-ups.

**HubSpot search (pattern)**

- Combine filters to enforce eligibility: `hs_lead_status` **EQ** `OPEN`, `linkedin_follow_up_sent` **EQ** `true`, `outreach_date` **LT** `<cutoff_iso>`, `email` **HAS_PROPERTY**, and (`email_follow_up_sent` is false OR has no value).
- Request properties: `firstname`, `lastname`, `email`, `company`, `jobtitle`, `lead_score`, `outreach_conversation`, `outreach_date`, `hs_lead_status`, `linkedin_follow_up_sent`, `email_follow_up_sent`, `hs_content_membership_notes` (or equivalent notes fields).
- **Sort** by **`outreach_date` ascending** (oldest last-touch first) if API allows; otherwise sort client-side.
- **Limit** per run: use a bounded batch (for example 5-15) unless owner says otherwise.

**Legacy / edge cases:** If **`outreach_date`** is empty on an `OPEN` contact, do not include them in this run. If complex OR filters are limited server-side, fetch a constrained `OPEN` batch and filter client-side to keep only records where `linkedin_follow_up_sent = true`, `outreach_date < cutoff`, and `email_follow_up_sent` is missing or false.

Read **`outreach_conversation` in full** so the follow-up avoids repeating the same hook or CTA.

## Step 2 - Prepare the Instantly follow-up

For each selected contact:

1. Confirm `email` and personalization fields (`firstname`, `company`, role context).
2. Review the last outreach block in `outreach_conversation`.
3. Draft one short follow-up email:
   - Acknowledge prior outreach briefly.
   - Add one new value point, insight, or relevant question.
   - Keep it concise (~3-6 short sentences).
   - Include one clear next step / CTA.

**Forbidden:** copy-pasting the original first-touch email, generic "just checking in" with no new substance, or multi-paragraph long-form emails.

## Step 3 - Send follow-up via Instantly

Use the `instantly-email` skill script to send from the correct sender account.
For this flow, set Instantly `eaccount` (sender email address) to **`burhanbilal10@gmail.com`**.

**Command pattern**

```bash
python3 workspace/skills/instantly-email/instantly_email.py test --json '{"to":"<lead_email>","eaccount":"burhanbilal10@gmail.com","subject":"<followup_subject>","body":{"text":"<followup_body>"}}'
```

If your workflow uses production send endpoints in your environment, switch to your approved send command while keeping the same content rules.

Confirm success from the API response before updating HubSpot.

## Step 4 - Update HubSpot after successful send

Use one send datetime (when send succeeded), ISO-8601 with timezone (UTC recommended), for example `2026-04-23T10:00:00.000Z`.

- **`outreach_conversation`**: **append** (do not replace). Preserve existing text and add a separator block, label **`Email follow-up (Instantly)`**, ISO time, subject, and full body.
- **`hs_lead_status`**: keep **`OPEN`** unless your portal policy explicitly changes it after follow-up.
- **`email_follow_up_sent`** (single checkbox): set to **true** after successful send.

**Example PATCH shape**

```
PATCH https://api.hubapi.com/crm/v3/objects/contacts/<contact_id>
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "properties": {
    "hs_lead_status": "OPEN",
    "outreach_conversation": "<existing value>\n\n---\nEmail follow-up (Instantly) sent <ISO datetime>.\nSubject: <subject>\nBody: <full body>",
    "email_follow_up_sent": "true"
  }
}
```

If send fails, log reason, do not PATCH as if sent, continue with next lead.

Use your portal's exact internal property name for **`email_follow_up_sent`** if it differs.

## Step 5 - Close run and report

1. End all transient work for this run.
2. Summary table:

| Lead | Company | Last `outreach_date` (before run) | Hours since last touch | Follow-up sent | `hs_lead_status` | `email_follow_up_sent` |
|------|---------|-----------------------------------|------------------------|---------------|------------------|------------------------|

If HubSpot or Instantly cannot be used reliably, do not fabricate send confirmations or patch rows.

## What this prompt is *not*

- **Not** first-touch cold outreach from `IN_PROGRESS`.
- **Not** LinkedIn DM follow-up workflow.
- **Not** inbox reply handling for inbound conversations.