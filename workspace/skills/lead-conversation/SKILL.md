---
name: lead-conversation
description: >-
  Work LinkedIn Sales Navigator inbox replies (unread threads): read each message and thread
  context, detect intent, and match the prospect in HubSpot by linkedin_sales_lead_url before
  sending any reply. Reply in-thread only when matched; include the HubSpot Meetings URL when
  they want to book. PATCH hs_lead_status to NOT_INTERESTED on opt-out and to MEETING_LINK_SENT
  when the meetings link is sent; log LinkedIn reply notes. Do not message unknown leads. Use
  when the user wants to handle Sales Navigator conversation replies, inbox follow-up, or
  process unread LinkedIn replies with HubSpot sync. Requires hubspot and linkedin-sales-navigator
  (browser); Sales Navigator session required.

metadata:
  openclaw:
    emoji: 💬
---


Use the **`hubspot`** skill and **`linkedin-sales-navigator`** skill together: open **LinkedIn Sales Navigator** at the **Unread-filtered inbox** URL below, prioritize **unread** threads, **read the prospect’s message in full** (and enough thread context to know what they are replying to), **detect their intent** (what they want from you), then **only reply** if that person **exists in HubSpot** matched by **Sales Navigator lead URL**. When you do reply, the **content must follow the detected intent** (answer their question, acknowledge interest, address objections, respect OOO / stop requests, etc.). If they show intent to **book a meeting** or **schedule a call** (and HubSpot match passed), include your **HubSpot Meetings** booking link (canonical URL below — send it **only** in-thread after the gate, never to unknown leads). If they are **not** in HubSpot (no matching `linkedin_sales_lead_url`), **do not reply**—leave the thread as-is or mark read per user preference without sending.

## Step 1 — Open Sales Navigator Inbox (Unread)

1. Open in the browser to ( **`filter=UNREAD`** is applied in the URL — do not substitute the plain inbox URL):

   ```
   https://www.linkedin.com/sales/inbox/compose?filter=UNREAD
   ```

2. Wait for the inbox UI to load. If not logged in or Sales Navigator is unavailable, stop and ask the user to log in, then resume at the same URL.

3. Use **`linkedin-sales-navigator`** / browser automation: stay in **Sales Navigator inbox** — do **not** switch to **`linkedin.com/messaging`** unless the user’s workflow explicitly requires it.

4. The list should already be **Unread**-scoped. If the UI resets the filter, re-select **Unread** / unread indicators so you work **unread threads first** (messages that are **not read** on your side).

---

## Step 2 — For each unread thread: read message → detect intent → HubSpot gate → reply aligned to intent

For each unread conversation (cap per run if needed, e.g. 10–20):

1. **Open the thread** and **read their message(s)** on the prospect side:
   - Capture the **full text** of the newest unread inbound (scroll inside the thread if truncated).
   - Skim **your prior outbound** and any earlier bubbles so you know **what they are responding to** (subject, offer, question you asked).

2. **Detect intent** — decide what they want **before** you write a reply. Use labels that fit the copy, for example:
   - **Interested / positive** — wants more info or a next step (if not yet asking to book, you may still **offer** the meetings link as a soft CTA when appropriate).
   - **Book meeting / schedule call** — explicit or strong implicit ask (e.g. “let’s book,” “send your calendar,” “when can we talk?”). After HubSpot match, reply with a **short** confirmation and the **HubSpot Meetings** URL from **HubSpot Meetings — booking a call** below (same rules as any outbound reply).
   - **Question** — specific ask (pricing, scope, timing, “how does X work?”).
   - **Objection or concern** — risk, fit, timing, competitor, “not sure.”
   - **Soft no / later** — not now, circle back, low energy.
   - **OOO / auto-reply** — away until a date; acknowledge briefly, no hard sell.
   - **Stop / unsubscribe / not interested** — **no pitch**; brief polite acknowledgment only (or silence per your policy); do not argue. When a HubSpot match exists, **always** update the contact (see **Step 3**): set **`hs_lead_status`** to **`NOT_INTERESTED`** so the pipeline reflects their intent, whether or not you send an acknowledgment in-thread.
   - **Unclear** — one **short** clarifying question is OK if HubSpot match exists and tone stays helpful, not pushy.

   Your **reply must match this intent** (e.g. answer the actual question; if they asked for a call link or time, reflect that; if they objected, address that point; do not send a generic template that ignores what they wrote).

3. **Obtain the Sales Navigator lead URL** for that person — required for HubSpot matching:
   - From the thread header / lead chip / “View in Sales Navigator” style link if shown, **or**
   - Open the lead in Sales Navigator from the thread so the URL is the **lead page** under `linkedin.com/sales/...` (same shape as **`linkedin_sales_lead_url`** in **`lead-outreach.md`**).

4. **Normalize the URL** for comparison: strip tracking query params (`utm_*`, etc.), trailing slashes, and fragment where safe so HubSpot search matches reliably.

5. **HubSpot lookup (mandatory before replying):** Search contacts for a row whose **`linkedin_sales_lead_url`** equals or clearly matches the normalized lead URL.

   Example (adjust object type date segment and token to your portal):

   ```
   POST https://api.hubapi.com/crm/v3/objects/contacts/search
   Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
   Content-Type: application/json

   {
     "filterGroups": [
       {
         "filters": [
           {
             "propertyName": "linkedin_sales_lead_url",
             "operator": "EQ",
             "value": "<normalized_sales_nav_lead_url>"
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
       "outreach_conversation",
       "hs_lead_status"
     ],
     "limit": 5
   }
   ```

   If **`EQ`** misses due to minor URL differences, fall back to a broader fetch (e.g. **`CONTAINS`** the stable lead path segment) and **confirm** an exact person match — never reply on a weak name-only match.

   After a match, re-read **`outreach_conversation`** (and similar fields) for **pathway** (Agency vs Business Owner) and prior outreach so the reply stays **consistent** with what they already know.

6. **Reply gate:**
   - **Match found in HubSpot** → **Compose and send** a reply in the Sales Navigator thread that **directly serves the detected intent** (see step 2), uses pathway context from HubSpot notes, and aligns with **`lead-outreach.md`** tone where applicable. Draft the **entire** message first, then insert it into the composer **once** (see **Composer workflow** under **Message format (Sales Navigator)**). If intent is **Book meeting / schedule call** (or equivalent), **include** `https://meetings-ap1.hubspot.com/mostly` in the message body as specified in **HubSpot Meetings — booking a call**. After sending, **Step 3** requires **`hs_lead_status`** → **`MEETING_LINK_SENT`**. Follow **Message format (Sales Navigator)** below so the sent text never contains escape artifacts.
   - **Match found + Stop / unsubscribe / not interested** — You may send **no** LinkedIn message (silence) or only the brief acknowledgment allowed in step 2. Either way, **Step 3** still applies: **`PATCH`** **`hs_lead_status`** → **`NOT_INTERESTED`** (do not leave them in an active outreach state).
   - **No HubSpot contact** with that **`linkedin_sales_lead_url`** → **Do not reply** (even if their intent is clear). Close or skip the thread; optionally note in your run summary: *unread from \<name\>; not in HubSpot — no reply sent.*

### Message format (Sales Navigator)

What you type or paste into the **Sales Navigator message composer** is what the prospect **literally sees**. Do **not** include programming-style escape sequences in that body.

- **Composer workflow (follow-ups and any reply):** Write the **full** message **first** (complete text, including where line breaks belong), **then** put it into the compose box **in one step** — e.g. paste the entire body at once, or select-all and replace if updating. Do **not** enter the message **line-by-line** or in many small keystrokes; the Sales Navigator composer can **overwrite or drop** earlier content when text is inserted incrementally.
- **Tone requirement:** Keep replies casual, human, and conversational. Write like a real person in a DM, not a formal email or rigid template.
- **Opening:** Do **not** start every reply with `Hi {name},`. In active back-and-forth threads, reply naturally without repeating greetings each time. Use a greeting only when it is the first touch in that thread or after a long gap.
- **Style constraints:** Use plain sentences and natural line breaks. Do **not** use bullet-style markers or decorative separators inside the message body (for example `-`, `_`, `---`) unless the prospect explicitly asked for a list.
- **Forbidden in the sent message:** the two-character sequences **`\n`**, **`\n\n`**, **`\t`**, **`\r`**, or any other backslash-escape meant for JSON/code strings. They look broken (“slash n”) or odd in chat and are a copy-paste mistake from drafts or tool output.
- **Use instead:** press **Enter / Return** in the composer for blank lines between paragraphs, or write one continuous paragraph with normal spaces. Separate the intro, the booking URL, and the sign-off with **real line breaks in the UI**, not the characters backslash + n.
- **If your draft text contains `\n`:** strip those tokens and re-type breaks in the LinkedIn field before sending.

**Bad (do not send):** `...book a time:\n\nhttps://meetings-ap1.hubspot.com/mostly\n\nLooking forward...`

**Good:** three real paragraphs in the composer — (1) thanks + offer, (2) the URL alone on its own line, (3) short closing line.

### HubSpot Meetings — booking a call

Use **only** this scheduling URL (your org’s HubSpot Meetings page — do not swap for a different slug unless the user updates this prompt):

```
https://meetings-ap1.hubspot.com/mostly
```

- **When:** Intent is **Book meeting / schedule call** (or they clearly pivot to booking in the same thread after you answered a question). **Never** send this link **before** the HubSpot **`linkedin_sales_lead_url`** match passes — same gate as any reply.
- **How:** One or two sentences of context, then the **full URL** on its own line (use a **real** line break in the composer — see **Message format (Sales Navigator)**) so they can tap/open it. No fake or placeholder links.
- **If unsure:** They asked a mix of questions **and** timing — answer the questions briefly, **then** offer the link as the natural next step.

---

## Step 3 — HubSpot contact updates after processing a matched lead

**Lead status field:** Pipeline updates use the contact property **`hs_lead_status`**. Allowed values in this workflow include at least **`NOT_INTERESTED`** (opt-out) and **`MEETING_LINK_SENT`** (you sent the HubSpot Meetings URL in-thread). Use the **exact** internal option strings your portal defines on `hs_lead_status` if they differ.

1. **Not interested / unsubscribe / stop** — When **`linkedin_sales_lead_url`** matched HubSpot **and** detected intent is **Stop / unsubscribe / not interested** (or clearly equivalent: “remove me,” “don’t contact,” hard no):
   - **`PATCH`** the contact: **`hs_lead_status`** → **`NOT_INTERESTED`**.
   - Append **`LinkedIn reply handled`** (or **`LinkedIn reply logged`**) with ISO date, intent label, and what they said — note whether you sent a brief in-thread acknowledgment or chose silence.

2. **Meeting link sent** — When you **included** `https://meetings-ap1.hubspot.com/mostly` in the Sales Navigator message (after the same HubSpot match gate as any reply):
   - **`PATCH`** the contact: **`hs_lead_status`** → **`MEETING_LINK_SENT`** (this is the **status**, not a separate property).
   - In notes, include **`HubSpot Meetings link sent`** plus the exact URL for the audit trail.

3. **Any other verified in-thread reply** (HubSpot matched, you sent a normal reply that is **not** covered solely by (1) or (2)) — **`PATCH`** to append **`LinkedIn reply handled`** (or **`LinkedIn reply logged`**) with ISO date, **detected intent**, short summary of what they said, that you replied in-thread, and a one-line note on **how your reply addressed their intent**. If you also sent the meetings link, apply **(2)** in the same **`PATCH`** where possible.

**Combine PATCHes** when multiple rules apply in one thread (e.g. reply + meetings link → notes + **`hs_lead_status`** → **`MEETING_LINK_SENT`**).

Skip HubSpot updates only when there was **no** HubSpot contact match. Skip **(1)–(3)** only if you truly took no action on a matched lead (rare); **(1)** applies even when you **did not** send a LinkedIn message but their intent was opt-out.

---

## Step 4 — Close tabs and report

1. Close LinkedIn tabs opened for this run.

2. Summary table:

| Thread / Lead | Their message read (Y/N) | Detected intent | Sales Nav lead URL resolved | In HubSpot? | Replied? | Meetings link sent? | `hs_lead_status` (e.g. NOT_INTERESTED / MEETING_LINK_SENT) |
|---------------|--------------------------|-------------------|-----------------------------|-------------|----------|---------------------|------------------------------------------------------------|

If the inbox cannot be read, **do not** invent messages or HubSpot matches and **do not** send replies.
