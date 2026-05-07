---
name: lead-sourcing
description: >-
  Run the Sales Navigator → HubSpot sourcing workflow: open a filtered people search, extract
  identity fields plus both LinkedIn URLs (public profile for Apollo, Sales Navigator lead URL),
  save leads to Agent's Lead List and send connection requests, and create HubSpot contacts with hs_lead_status NEW—without
  scoring or qualification (those live in the lead-qualification prompt). Use when the user
  wants to source leads, push Sales Nav prospects into CRM, run get-leads, or fill the top of
  the funnel before Apollo/qualification. Requires linkedin-sales-nav-lead-actions (save + connect
  via CLI) with linkedin-sales-navigator (browser fallback) and hubspot skills.

metadata:
  openclaw:
    emoji: 🎯
---

Use **`linkedin-sales-nav-lead-actions`** (save + connect CLI), **`linkedin-sales-navigator`** (browser for search and CLI fallback), and **`hubspot`** together to **source leads** into HubSpot (identity + URLs + basics). **Scoring and qualification** happen in the lead-qualification workflow, not in this skill.

## Step 1 — Fetch leads from LinkedIn Sales Navigator

Open the following pre-filtered LinkedIn Sales Navigator URL directly in the browser:

```
https://www.linkedin.com/sales/search/people?query=(spellCorrectionEnabled%3Atrue%2CrecentSearchParam%3A(id%3A5618075884%2CdoLogHistory%3Atrue)%2Cfilters%3AList((type%3ACOMPANY_HEADCOUNT%2Cvalues%3AList((id%3AB%2Ctext%3A1-10%2CselectionType%3AINCLUDED)%2C(id%3AC%2Ctext%3A11-50%2CselectionType%3AINCLUDED)))%2C(type%3ALEAD_LIST%2Cvalues%3AList((id%3A7449361383735050240%2Ctext%3AAgent%2527s%2520Lead%2520List%2CselectionType%3AEXCLUDED)))%2C(type%3AREGION%2Cvalues%3AList((id%3A103644278%2Ctext%3AUnited%2520States%2CselectionType%3AINCLUDED)%2C(id%3A101165590%2Ctext%3AUnited%2520Kingdom%2CselectionType%3AINCLUDED)%2C(id%3A101174742%2Ctext%3ACanada%2CselectionType%3AINCLUDED)))%2C(type%3ACURRENT_TITLE%2Cvalues%3AList((id%3A35%2Ctext%3AFounder%2CselectionType%3AINCLUDED)%2C(id%3A1%2Ctext%3AOwner%2CselectionType%3AINCLUDED)%2C(id%3A103%2Ctext%3ACo-Founder%2CselectionType%3AINCLUDED)%2C(id%3A5%2Ctext%3ADirector%2CselectionType%3AINCLUDED)%2C(id%3A16%2Ctext%3AManaging%2520Director%2CselectionType%3AINCLUDED)%2C(id%3A8%2Ctext%3AChief%2520Executive%2520Officer%2CselectionType%3AINCLUDED)))%2C(type%3APOSTED_ON_LINKEDIN%2Cvalues%3AList((id%3ARPOL%2Ctext%3APosted%2520on%2520LinkedIn%2CselectionType%3AINCLUDED))))%2Ckeywords%3A%2522marketing%2520agency%2522%2520OR%2520%2522digital%2520marketing%2522%2520OR%2520%2522web%2520design%2522%2520OR%2520%2522web%2520development%2520agency%2522%2520OR%2520%2522creative%2520agency%2522%2520OR%2520%2522branding%2520agency%2522%2520OR%2520%2522growth%2520agency%2522%2520OR%2520%2522growth%2520marketing%2522%2520OR%2520%2522performance%2520marketing%2522)&sessionId=49xjygLERW%2B8gwX92thMFQ%3D%3D
```

This URL has all filters pre-applied:

- **Keywords:** `"marketing agency" OR "digital marketing" OR "web design" OR "web development agency" OR "creative agency" OR "branding agency" OR "growth agency" OR "growth marketing" OR "performance marketing"`
- **Company Headcount:** 1–10 and 11–50 employees
- **Job Title / Seniority:** Founder, Owner, Co-Founder, Director, Managing Director, CEO
- **Geography:** United States, United Kingdom, Canada
- **Spotlights:** Posted on LinkedIn (last 30 days)
- **Excluded:** Agent's Lead List (no duplicates)

Collect the lead from the results.

1. Click on the lead's name to open their LinkedIn Sales Navigator profile in a new tab.
2. Analyze the profile and extract the following information:
   - First Name
   - Last Name
   - Company Name
   - Job Title / Role
   - **Email and phone** — Open **Contact information** on the Sales Navigator lead profile (every lead has this section/panel). Check whether they **listed** an **email** and/or **phone**—typically separate rows with icons (e.g. envelope vs handset)—and copy only real values. If a row is empty, shows **Add contact info**, or is not a usable address/number, treat that field as not found. Email can rarely appear elsewhere on the profile or in visible activity; capture it if so.
   - **LinkedIn profile URL** — public member URL (`https://www.linkedin.com/in/...`). On the Sales Navigator lead profile, beside **Message**, open the **⋯ (three-dot) overflow menu**, then choose **Copy LinkedIn.com URL** from the dropdown; paste to capture the link. Alternatives: **View LinkedIn profile** (then copy from the browser bar) or **View in LinkedIn** / the profile’s public link if you already have it. Used for **Apollo** enrichment (`apollo.py enrich --linkedin`).
   - **LinkedIn Sales Navigator lead URL** — full URL from the browser address bar while on the **Sales Navigator** lead profile (e.g. `https://www.linkedin.com/sales/lead/...`). Used to reopen this lead in Sales Navigator later (search, save, outreach).
   - Recent activity / posts (note any relevant topics they've posted about)
   - Years of experience / seniority signals
   - Any mutual connections or shared interests
   - **Company website URL** (if shown on profile or company card) — optional capture for downstream qualification; no scoring or site “quality” judgment here.

3. Close the profile tab once extraction is complete, and return to the search results to move on to the next lead.

## Step 2 — Save each lead to Agent's Lead List, then send a connection request

Before pushing to HubSpot, for each lead collected, use the **`linkedin-sales-nav-lead-actions`** skill and the Sales Navigator **lead URL** you captured (`https://www.linkedin.com/sales/lead/...`). Prefer **`--openclaw`** so the script attaches to the same browser session as the rest of the workflow (`openclaw browser --browser-profile openclaw start` / `status` if needed). Full CLI reference: [`workspace/skills/linkedin-sales-nav-lead-actions/SKILL.md`](../linkedin-sales-nav-lead-actions/SKILL.md).

### 2a — Save to list (script first, browser if needed)

1. **Preferred:** run the save action:

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action save \
  --profile-url '<Sales Navigator lead URL>'
```

(`--list-name` defaults to **Agent's Lead List**; pass it explicitly if you use another list.)

2. **If the script fails** (e.g. `ok: false`, timeout, or broken selectors): fall back to the **`linkedin-sales-navigator`** browser flow — open the lead profile, click **Save** button, and choose **Agent's Lead List**.

### 2b — Connection request (after save)

Once the lead is on the list, send the connection request with the **same** `--profile-url`:

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action connect \
  --profile-url '<Sales Navigator lead URL>' \
  --note "Optional invitation note."
```

If connect fails after a successful save, use browser automation (**⋯** next to Message → **Connect**) as a last resort, per **`linkedin-sales-nav-lead-actions`**.

This ensures every processed lead is tracked in Sales Navigator and excluded from future searches (preventing duplicates via the `LEAD_LIST` exclusion filter in the URL).

## Step 3 — Push each lead into HubSpot as a Contact

For each lead collected, create a contact in HubSpot using the `hubspot` skill with these fields mapped:

| LinkedIn field                                           | HubSpot property                                                                                                                     |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| First Name                                               | `firstname`                                                                                                                          |
| Last Name                                                | `lastname`                                                                                                                           |
| Company Name                                             | `company`                                                                                                                            |
| Job Title / Role                                         | `jobtitle`                                                                                                                           |
| LinkedIn profile URL (`linkedin.com/in/...`)             | `hs_linkedin_url` — **primary for Apollo** (`--linkedin`). |
| Sales Navigator lead URL (`linkedin.com/sales/lead/...`) | `linkedin_sales_lead_url`  |
| Email                                                    | `email` (leave blank if not found)                                                                                                   |
| Phone                                                    | `phone` (leave blank if not found)                                                                                                   |
| —                                                        | `hs_lead_status` → `NEW`                                                                                                             |

Do **not** set `hs_lead_grade` or qualification notes here — the qualification workflow fills those after Apollo + scoring.

Use the HubSpot Create Contact API for each lead:

```
POST https://api.hubapi.com/crm/v3/objects/contacts
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN

{
  "properties": {
    "firstname": "<First Name>",
    "lastname": "<Last Name>",
    "company": "<Company Name>",
    "jobtitle": "<Role>",
    "hs_linkedin_url": "<LinkedIn Public profile URL>",
    "linkedin_sales_lead_url": "<Sales Navigator lead URL from address bar>",
    "email": "<Email or omit if not found>",
    "phone": "<Phone or omit if not found>",
    "hs_lead_status": "NEW"
  }
}
```

**URL rules:** `hs_linkedin_url` must be the public profile link. `linkedin_sales_lead_url` must be the **Sales Navigator** page URL only — never put the SN URL into `hs_linkedin_url` (Apollo expects a normal `linkedin.com/in/...` or equivalent member URL).


## Step 4 — Report results

After all leads are pushed, show a summary table with:

- Lead name, company, role, **profile URL** (`hs_linkedin_url`), **Sales Navigator lead URL**, email (or "N/A"), phone (or "N/A"), HubSpot contact ID returned from the API

If any contact creation fails (e.g. duplicate email), note the error and continue with the next lead.

Once the summary table is complete, close all remaining browser tabs that were opened during this session (Sales Navigator search results tab and any residual profile tabs).

## Step 5 — Send sourced leads to Slack

After finishing sourcing and HubSpot pushes, send a Slack message listing which leads were sourced in this run (name, company, and role).

Use this command format:

```bash
openclaw message send --channel slack --target "channel:C0B0GAZ032L" --message "Sourced leads: <Lead 1 — Company — Role>; <Lead 2 — Company — Role>; ..."
```
