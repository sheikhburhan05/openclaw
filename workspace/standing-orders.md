# Standing Orders

Programs below grant standing authority within stated boundaries. **Lead sourcing** lives in `skills/lead-sourcing/SKILL.md`; **lead qualification** in `skills/lead-qualification/SKILL.md`; **lead outreach** in `skills/lead-outreach/SKILL.md` (includes **InMail credit read** and **weekday-only monthly pacing** before HubSpot fetch); **connection outreach** (same **`IN_PROGRESS`** queue shape; verify **accepted connection** on Sales Navigator; message via **free thread only** — **no InMail**; **`is_connected`** HubSpot flag) in `skills/connection-outreach/SKILL.md`; **lead conversation** (Sales Navigator inbox replies) in `skills/lead-conversation/SKILL.md`; **LinkedIn follow-up** in `skills/linkedin-follow-up/SKILL.md`; **email follow-up** in `skills/email-follow-up/SKILL.md`. This file stays the **scope / triggers / gates** layer; execution follows those references verbatim.

---

## Program: Lead Sourcing (Sales Navigator → HubSpot)

**Authority:** Run the end-to-end **lead sourcing** workflow only as defined in `skills/lead-sourcing/SKILL.md` (lead-sourcing skill): open the pre-filtered Sales Navigator people search, extract identity fields plus **both** LinkedIn URLs (public `linkedin.com/in/...` for Apollo and Sales Navigator lead URL from the address bar), save each processed lead to **Agent's Lead List**, create HubSpot contacts with `hs_lead_status` = `NEW`, and report a summary table with HubSpot contact IDs. Use the **linkedin-sales-navigator** and **hubspot** skills as specified there.

**Trigger:**

- **On-demand:** Whenever the owner asks to source leads, run get-leads, push Sales Nav prospects into the CRM, or fill the top of the funnel before Apollo/qualification.
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/lead-sourcing/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** None for standard runs **inside** the skill’s rules (browser + HubSpot API only). If the owner has classified “messages that leave the machine” broadly, treat **delivering summaries to external channels** per `AGENTS.md` red lines. Escalate before bulk or experimental changes to HubSpot property definitions beyond creating the named custom properties in the skill.

**Escalation (stop and ask or report clearly):**

- LinkedIn Sales Navigator session missing, expired, or blocked; cannot reach the saved search URL.
- HubSpot returns persistent errors after one retry with adjusted approach (e.g. create missing `hs_linkedin_url` / Sales Navigator URL properties, then retry); duplicate or invalid email called out in the skill — log and continue with remaining leads, then summarize failures.
- Ambiguity about how many leads to process in one run — default to what the owner specified; if unspecified, process a **small bounded batch** (e.g. one to a few leads) and report rather than scraping at scale unattended.

### Execution steps (summary)

1. **Read and follow** `skills/lead-sourcing/SKILL.md` for Steps 1–5 (Sales Nav → save to list → round-robin account → HubSpot create contact → report and close tabs).
2. **Round-robin account selection (Step 2b):** For every qualified lead, read `workspace/state/outreach_account.json`, toggle to the opposite account (`openclaw` ↔ `openclaw-2`), **write the new `last_used` back to the state file immediately** (before the connect request), then send the connection request using that browser profile. Store the chosen account as `outreach_account` in HubSpot alongside the contact.
3. **Execute–Verify–Report:** After each push, confirm the API response includes a contact id where success; verify summary table fields match what was sent; report failures with diagnosis, no silent drops.
4. **Hygiene:** Close browser tabs as the skill requires after the summary.

### What NOT to do

- Do **not** score, qualify, or set `hs_lead_grade` / qualification notes here — that belongs to `skills/lead-qualification/SKILL.md`.
- Do **not** put the Sales Navigator lead URL into **`hs_linkedin_url`**; Apollo expects the public profile URL only.
- Do **not** skip saving leads to **Agent's Lead List** before or as part of HubSpot push — that maintains the exclusion filter and avoids duplicates.
- Do **not** acknowledge “sourced” without completed HubSpot creates (or documented skips/errors) and the closing summary table.
- Do **not** skip the state file write in Step 2b — the round-robin breaks if `workspace/state/outreach_account.json` is not updated every run.

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.

---

## Program: Lead Qualification (HubSpot → Apollo → Sales Navigator → HubSpot)

**Authority:** Run the end-to-end **lead qualification** workflow only as defined in `skills/lead-qualification/SKILL.md` (lead-qualification skill): search HubSpot for **`hs_lead_status` = `NEW`** contacts with a LinkedIn URL, enrich with **Apollo** (person + organization via `workspace/skills/apollo-enrichment/apollo.py`), complete the **mandatory** Sales Navigator profile review and **website visits** (Step 3), classify (**Agency** / **Business Owner** / **Disqualified**), apply the **correct scoring model** and priority band, **PATCH** the contact (including **`lead_score`**, **`lead_score_details`** with full per-criterion reasoning and audit context per the skill, status, and other fields), and output the closing summary table. Use the **hubspot**, **apollo-enrichment**, and **linkedin-sales-navigator** (browser) capabilities as specified in that skill.

**Trigger:**

- **On-demand:** Whenever the owner asks to qualify leads, score NEW contacts, run Apollo + Sales Nav qualification, or move contacts from sourcing toward outreach.
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/lead-qualification/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** None for standard runs **inside** the skill’s rules (HubSpot API + Apollo CLI + browser only). If the owner has classified “messages that leave the machine” broadly, treat **delivering summaries to external channels** per `AGENTS.md` red lines. Escalate before bulk edits to HubSpot property definitions, custom scoring properties, or non-standard `hs_lead_status` values not aligned with the **Lead Outreach** program and `skills/lead-outreach/SKILL.md`.

**Escalation (stop and ask or report clearly):**

- LinkedIn Sales Navigator session missing, expired, or blocked; cannot open the lead profile or company panel for Step 3.
- **Apollo** unavailable after reasonable retry (auth, rate limit, 5xx) — continue using the skill’s “Apollo off” path (Sales Navigator + website only) and document in notes; stop if you cannot complete Step 3 at all.
- HubSpot search or **PATCH** returns persistent errors after one retry with adjusted payload (missing properties, validation); log contact id + error, continue with remaining contacts if applicable, then summarize failures.
- Ambiguity about how many contacts to qualify in one run — default to what the owner specified; if unspecified, process a **small bounded batch** (e.g. the skill’s default search limit or one to a few contacts) and report rather than qualifying at scale unattended.

### Execution steps (summary)

1. **Read and follow** `skills/lead-qualification/SKILL.md` for Steps 1–8 (search → Apollo → Sales Nav + websites → classify → score → bands → PATCH → report).
2. **Execute–Verify–Report:** After each PATCH, confirm success or capture the error; ensure notes append preserves prior content; report the summary table with HubSpot updated yes/no per row.
3. **Hygiene:** Close browser tabs as the skill requires after each profile/site review.

### What NOT to do

- Do **not** run **lead sourcing** (saved search → new contacts) inside this program — that belongs to the Lead Sourcing program and `skills/lead-sourcing/SKILL.md`.
- Do **not** skip **Step 3** (Sales Navigator profile + external website assessment) because Apollo returned data; Apollo is a cross-check, not a substitute for the browser steps.
- Do **not** put the Sales Navigator lead URL into **`hs_linkedin_url`**; store the **public** `linkedin.com/in/...` profile URL there (Apollo expects that shape).
- Do **not** send LinkedIn DMs, email campaigns, or other outreach here — that is the **Lead Outreach** program (`skills/lead-outreach/SKILL.md`) or **Connection Outreach** program (`skills/connection-outreach/SKILL.md`) after contacts are qualified and status allows pickup.

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.

---

## Program: Lead Outreach (HubSpot → Sales Navigator message → HubSpot)

**Authority:** Run the end-to-end **lead outreach** workflow only as defined in `skills/lead-outreach/SKILL.md` (lead-outreach skill): **first** read remaining **Sales Navigator InMail credits** in the browser (snapshot), compute **today’s send cap** from **`credits_remaining // working_days_remaining`** counting **weekdays only** (Monday–Friday) from **today** through month-end (see Step 0 in the skill); optionally verify math with `skills/lead-outreach/scripts/inmail_monthly_pacing.py`. Then search HubSpot for **`hs_lead_status` = `IN_PROGRESS`** contacts with **`lead_score`** and **`linkedin_sales_lead_url`** (Sales Navigator lead page — **only** URL used to open and send; do not use public profile URLs for messaging), **cap the HubSpot fetch** at that send budget, sort by **`lead_score` descending**, open each lead in Sales Navigator, send a **LinkedIn Message** (subject + body) pathway-aware per the skill, **PATCH** **`hs_lead_status`**, **`outreach_date`** (full datetime), and **`outreach_conversation`** (append sent copy), and report the summary table. Use the **hubspot** and **linkedin-sales-navigator** (browser) skills as specified there.

**Trigger:**

- **On-demand:** Whenever the owner asks to message qualified leads, run LinkedIn outreach, work the post-qualification queue, or contact `IN_PROGRESS` leads with scores.
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/lead-outreach/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** This program **sends outbound LinkedIn messages** (they leave the machine). Follow **`AGENTS.md`** red lines and the owner’s policy on outbound messages; obtain explicit approval when required before clicking **Send**. None beyond that for standard runs **inside** the skill if the owner has granted standing authority for this program.

**Escalation (stop and ask or report clearly):**

- LinkedIn Sales Navigator session missing, expired, or blocked; cannot open **`linkedin_sales_lead_url`** or the **Message** UI.
- **InMail credits** cannot be read or are **zero** — do not exceed credits; stop outbound sends for this program until credits refresh or the owner overrides with explicit instruction.
- Contact is **`IN_PROGRESS`** but missing **`linkedin_sales_lead_url`** — backfill via lead sourcing / qualification before outreach, or skip with a logged reason.
- HubSpot search or **PATCH** returns persistent errors after one retry; log contact id + error, continue with remaining contacts if applicable, then summarize failures.
- Send blocked (rate limits, existing thread, UI) — log reason, adjust PATCH per skill, continue.
- Ambiguity about how many contacts to message in one run — default to what the owner specified; if unspecified, use **`sends_budget_today`** from Step 0 (InMail pacing); never exceed that budget in one run unless the owner explicitly overrides (e.g. month-end catch-up).

### Execution steps (summary)

1. **Read and follow** `skills/lead-outreach/SKILL.md` for **all** steps, including **Step 0** (InMail credits → weekday pacing → **`sends_budget_today`**).
2. **Execute–Verify–Report:** After each send + PATCH, confirm HubSpot reflects **`outreach_date`**, appended **`outreach_conversation`**, and updated **`hs_lead_status`** per the skill; report credits read, working days remaining, budget used, and the summary table with sent/updated status per row.
3. **Hygiene:** Close LinkedIn tabs as the skill requires after each contact or run.

### What NOT to do

- Do **not** run **lead sourcing** or **lead qualification** here — use `skills/lead-sourcing/SKILL.md` and `skills/lead-qualification/SKILL.md` respectively.
- Do **not** open **`linkedin_url`** or **`hs_linkedin_url`** to send messages in this program; use **`linkedin_sales_lead_url`** only.
- Do **not** skip **Step 0** or message more leads in one run than **`sends_budget_today`** unless the owner explicitly overrides pacing.
- Do **not** skip the HubSpot **PATCH** after a successful send (or document intentional skip with reason).
- Do **not** run **Sales Navigator inbox replies** or process **unread inbound threads** here — that is the **Lead Conversation** program and `skills/lead-conversation/SKILL.md` (this program is **outbound** first contact from the queue).
- Do **not** run **`skills/connection-outreach/SKILL.md`** here — that program verifies **accepted connection** and **`is_connected`** without **InMail** pacing; use **Connection Outreach** when the owner wants post-connection messaging only.

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.

---

## Program: Connection Outreach (HubSpot IN_PROGRESS → verify connection → Sales Navigator message → HubSpot)

**Authority:** Run the end-to-end **connection outreach** workflow only as defined in `skills/connection-outreach/SKILL.md` (connection-outreach skill): search HubSpot for **`hs_lead_status` = `IN_PROGRESS`** contacts with **`lead_score`** and **`linkedin_sales_lead_url`** (same fetch shape as **`lead-outreach`**; Sales Navigator lead page **only** — do not use public profile URLs to open or send). Open each lead in Sales Navigator, **verify they accepted the connection** (**1st-degree** / connected UI — **not** pending invite, **not** InMail-only path). **Only** if connected, send a **LinkedIn Message** (subject + body when the UI requires it) pathway-aware per the skill — **no InMail credits**. Then **PATCH** **`hs_lead_status`**, **`outreach_date`** (full datetime), **`outreach_conversation`** (append sent copy), and **`is_connected`** = **`true`**. If **not** connected yet, **skip** send and **do not** set **`is_connected`** true. Use **bounded batch** sizing per the skill (there is **no** InMail pacing Step 0). Use the **hubspot** and **linkedin-sales-navigator** (browser) skills as specified there.

**Trigger:**

- **On-demand:** Whenever the owner asks to message **`IN_PROGRESS`** leads **after** connection acceptance only, avoid **InMail** spend, sync **`is_connected`** from Sales Navigator, or run the **post-connection** queue (distinct from **Lead Outreach** InMail pacing).
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/connection-outreach/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** This program **sends outbound LinkedIn messages** when the connected path is confirmed (they leave the machine). Follow **`AGENTS.md`** red lines and the owner’s policy on outbound messages; obtain explicit approval when required before clicking **Send**. None beyond that for standard runs **inside** the skill if the owner has granted standing authority for this program.

**Escalation (stop and ask or report clearly):**

- LinkedIn Sales Navigator session missing, expired, or blocked; cannot open **`linkedin_sales_lead_url`** or read connection state from the profile chrome.
- HubSpot missing **`is_connected`** property definition — create the boolean/checkbox property per the skill before PATCHing, or escalate.
- Contact is **`IN_PROGRESS`** but missing **`linkedin_sales_lead_url`** — backfill via lead sourcing / qualification before outreach, or skip with a logged reason.
- HubSpot search or **PATCH** returns persistent errors after one retry; log contact id + error, continue with remaining contacts if applicable, then summarize failures.
- Send blocked (rate limits, UI, thread errors) — log reason; **do not** mark **`is_connected`** true or **`OPEN`** if send did not succeed, unless portal policy says otherwise.
- Ambiguity about batch size — default to owner instruction; if unspecified, use the skill’s **small bounded batch**; **never** send via **InMail** inside this program.

### Execution steps (summary)

1. **Read and follow** `skills/connection-outreach/SKILL.md` for **all** steps (fetch → verify connection on Sales Nav → message only if connected → PATCH including **`is_connected`**).
2. **Execute–Verify–Report:** After each verified-connected send + PATCH, confirm HubSpot reflects **`outreach_date`**, appended **`outreach_conversation`**, **`hs_lead_status`** per the skill, and **`is_connected`** = **`true`**; report skipped-not-connected rows and the summary table.
3. **Hygiene:** Close LinkedIn tabs as the skill requires after each contact or run.

### What NOT to do

- Do **not** run **`skills/lead-outreach/SKILL.md`** here — that program reads **InMail credits** and weekday pacing; **this** program **never** consumes **InMail** and requires **accepted connection** first.
- Do **not** open **`linkedin_url`** or **`hs_linkedin_url`** to send messages; use **`linkedin_sales_lead_url`** only.
- Do **not** send when only **InMail** is available or connection is **pending** — skip until a later run.
- Do **not** set **`is_connected`** **`true`** without verifying connected state on Sales Navigator (and generally without a successful send unless portal policy defines otherwise).
- Do **not** skip HubSpot **PATCH** after a successful connected-path send (status, **`outreach_date`**, **`outreach_conversation`**, **`is_connected`**).

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.

---

## Program: Lead Conversation (Sales Navigator inbox → HubSpot)

**Authority:** Run the end-to-end **lead conversation** workflow only as defined in `skills/lead-conversation/SKILL.md` (lead-conversation skill): open the **LinkedIn Sales Navigator** **Unread**-filtered inbox, read each thread and **detect intent**, **search HubSpot** for a contact whose **`linkedin_sales_lead_url`** matches the Sales Nav lead (mandatory **before** any reply), **reply in-thread** only when that match exists; include the **HubSpot Meetings** booking URL when intent is to book; **`PATCH`** **`hs_lead_status`** to **`NOT_INTERESTED`** (opt-out) or **`MEETING_LINK_SENT`** (meetings link sent) per the skill, and append **LinkedIn reply** notes; **do not** message leads who are **not** in HubSpot on that property. Use the **hubspot** and **linkedin-sales-navigator** (browser) skills as specified there.

**Trigger:**

- **On-demand:** Whenever the owner asks to handle **Sales Navigator inbox** replies, process **unread** threads, run LinkedIn **conversation** follow-up, or sync **inbound** LinkedIn messages to HubSpot with the lead URL gate.
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/lead-conversation/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** This program **sends in-thread LinkedIn replies** when a HubSpot match exists and a reply is appropriate. Follow **`AGENTS.md`** red lines and the owner’s policy; obtain explicit approval when required before clicking **Send**. The skill **never** replies to threads where **`linkedin_sales_lead_url`** does not match a contact (no gate pass).

**Escalation (stop and ask or report clearly):**

- LinkedIn Sales Navigator session missing, expired, or blocked; cannot open the **inbox** URL or threads.
- Inbox UI unreadable or rate-limited — do not invent messages; summarize the failure.
- HubSpot search or **PATCH** returns persistent errors after one retry; log contact id + error, continue with remaining threads if applicable, then summarize failures.
- Ambiguity about how many threads to process in one run — default to what the owner specified; if unspecified, use a **small bounded batch** (e.g. 10–20 in the skill) and report.

### Execution steps (summary)

1. **Read and follow** `skills/lead-conversation/SKILL.md` for Steps 1–4 (inbox → per-thread read/match → reply or skip → HubSpot PATCH → close tabs → report).
2. **Execute–Verify–Report:** After each thread, confirm whether HubSpot matched; if you replied or **PATCH**ed (including opt-out without a send), confirm HubSpot reflects **notes** and **`hs_lead_status`** as the skill requires; report the summary table.
3. **Hygiene:** Close LinkedIn tabs as the skill requires after the run.

### What NOT to do

- Do **not** run **lead sourcing**, **lead qualification**, or **`IN_PROGRESS`** outbound messaging here — use `skills/lead-sourcing/SKILL.md`, `skills/lead-qualification/SKILL.md`, and for outbound queue programs **`skills/lead-outreach/SKILL.md`** or **`skills/connection-outreach/SKILL.md`** per standing orders.
- Do **not** send an in-thread reply **without** a HubSpot contact match on **`linkedin_sales_lead_url`** (skill gate).
- Do **not** switch to **`linkedin.com/messaging`** instead of **Sales Navigator inbox** unless the owner’s workflow explicitly requires it (per skill).
- Do **not** skip **PATCH** when the skill requires it (e.g. **`NOT_INTERESTED`**, **`MEETING_LINK_SENT`**, reply-handled notes).

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.

---

## Program: LinkedIn Follow-Up (HubSpot OPEN 48h+ → Sales Navigator message → HubSpot)

**Authority:** Run the end-to-end **LinkedIn follow-up** workflow only as defined in `skills/linkedin-follow-up/SKILL.md` (linkedin-follow-up skill): search HubSpot for **`hs_lead_status` = `OPEN`** contacts whose **`outreach_date`** is at least **48 hours old**, with **`linkedin_sales_lead_url`** present and **`linkedin_follow_up_sent`** missing/false; open each Sales Navigator lead URL, send one short **second-touch** in the existing thread, then **PATCH** HubSpot by appending **`outreach_conversation`** and setting **`linkedin_follow_up_sent`** to true. Do **not** update `outreach_date` in this flow. Use the **hubspot** and **linkedin-sales-navigator** skills as specified there.

**Trigger:**

- **On-demand:** Whenever the owner asks to send second-touch LinkedIn follow-ups for OPEN leads after an initial outreach.
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/linkedin-follow-up/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** This program **sends outbound LinkedIn messages** (they leave the machine). Follow **`AGENTS.md`** red lines and the owner’s outbound-message policy; obtain explicit approval when required before clicking **Send**. None beyond that for standard runs inside the skill if standing authority has been granted.

**Escalation (stop and ask or report clearly):**

- LinkedIn Sales Navigator session missing, expired, or blocked; cannot open **`linkedin_sales_lead_url`** or message UI.
- HubSpot search or **PATCH** returns persistent errors after one retry; log contact id + error, continue where safe, then summarize failures.
- Contact lacks required fields for this flow (`linkedin_sales_lead_url`, valid `outreach_date`) or thread/send UI prevents delivery; skip with explicit reason.
- Ambiguity about batch size for a run — default to owner instruction; if unspecified, use a **small bounded batch** and report.

### Execution steps (summary)

1. **Read and follow** `skills/linkedin-follow-up/SKILL.md` for Steps 1–5 (search eligible OPEN leads → open Sales Nav lead pages → send follow-up in-thread → PATCH HubSpot → close tabs/report).
2. **Execute–Verify–Report:** After each send + PATCH, confirm the message appears in thread and HubSpot reflects appended `outreach_conversation` plus `linkedin_follow_up_sent=true`; include failures with reasons.
3. **Hygiene:** Close LinkedIn tabs opened for the run.

### What NOT to do

- Do **not** use public profile URLs (`linkedin_url`, `hs_linkedin_url`) to send; use **`linkedin_sales_lead_url`** only.
- Do **not** run first-touch outreach from the **`IN_PROGRESS`** queue here — that belongs to **`skills/lead-outreach/SKILL.md`** (InMail-paced) or **`skills/connection-outreach/SKILL.md`** (post-connection).
- Do **not** fabricate send confirmations or PATCH as sent when delivery fails.
- Do **not** overwrite `outreach_conversation`; always append per the skill format.

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.

---

## Program: Email Follow-Up (HubSpot OPEN + LinkedIn follow-up done, 72h+ → Instantly → HubSpot)

**Authority:** Run the end-to-end **email follow-up** workflow only as defined in `skills/email-follow-up/SKILL.md` (email-follow-up skill): search HubSpot for **`hs_lead_status` = `OPEN`** contacts where **`linkedin_follow_up_sent` = true**, **`outreach_date`** is at least **72 hours old**, email exists, and **`email_follow_up_sent`** is missing/false; send one concise new follow-up email through Instantly (default sender `burhanbilal10@gmail.com` per skill), then **PATCH** HubSpot by appending **`outreach_conversation`** and setting **`email_follow_up_sent`** to true. Do **not** update `outreach_date` in this flow. Use the **hubspot** and **instantly-email** skills as specified there.

**Trigger:**

- **On-demand:** Whenever the owner asks to send post-LinkedIn email follow-ups for OPEN leads after the required delay window.
- **Scheduled (optional):** If a cron job is added, its message should say only to execute **this program** per `standing-orders.md` / `skills/email-follow-up/SKILL.md` — do not duplicate the full workflow in the cron body.

**Approval gate:** This program **sends outbound email** (messages leave the machine). Follow **`AGENTS.md`** red lines and owner policy for external sends; obtain explicit approval when required before initiating send commands.

**Escalation (stop and ask or report clearly):**

- Instantly API/script unavailable after reasonable retry (auth, rate limit, 5xx, sender config), or send confirmation cannot be verified.
- HubSpot search or **PATCH** returns persistent errors after one retry; log contact id + error, continue where safe, then summarize failures.
- Contact missing required email data or has invalid address; skip and report.
- Ambiguity about run size — default to owner instruction; if unspecified, process a **small bounded batch** and report.

### Execution steps (summary)

1. **Read and follow** `skills/email-follow-up/SKILL.md` for Steps 1–5 (search eligible contacts → draft concise follow-up → send via Instantly → PATCH HubSpot → report).
2. **Execute–Verify–Report:** Confirm Instantly success before PATCH; after each PATCH confirm appended `outreach_conversation` plus `email_follow_up_sent=true`.
3. **Hygiene:** End transient run state after completion and provide summary table.

### What NOT to do

- Do **not** send before confirming prerequisites (`linkedin_follow_up_sent=true`, `outreach_date` older than 72h, `email_follow_up_sent` missing/false).
- Do **not** copy-paste first-touch outreach content as the follow-up; add new value/CTA per skill.
- Do **not** mark `email_follow_up_sent` true when send fails or is unconfirmed.
- Do **not** overwrite existing `outreach_conversation`; append only.

### Related automation

- Time-based runs: pair with [cron jobs](https://docs.openclaw.ai/automation/cron-jobs) whose prompt references this program by name and file path, per [Standing Orders](https://docs.openclaw.ai/automation/standing-orders) documentation.
