---
name: lead-sourcing
description: >-
  Run the Sales Navigator → HubSpot sourcing workflow: open a filtered people search, extract
  identity fields plus both LinkedIn URLs (public profile for Apollo, Sales Navigator lead URL),
  apply sourcing-time disqualification (AI/agency/crypto/enterprise/etc.—no HubSpot push),
  save qualified leads to Agent's Lead List and send connection requests, and create HubSpot contacts with hs_lead_status NEW—without
  scoring or qualification (those live in the lead-qualification prompt). Use when the user
  wants to source leads, push Sales Nav prospects into CRM, run get-leads, or fill the top of
  the funnel before Apollo/qualification. Requires linkedin-sales-nav-lead-actions (save + connect
  via CLI) with linkedin-sales-navigator (browser fallback) and hubspot skills.

metadata:
  openclaw:
    emoji: 🎯
---

Use **`linkedin-sales-nav-lead-actions`** (save + connect CLI), **`linkedin-sales-navigator`** (browser for search and CLI fallback), and **`hubspot`** together to **source leads** into HubSpot (identity + URLs + basics). Before HubSpot, run **sourcing disqualification** on each profile (see below)—**disqualified leads are not pushed to HubSpot**. **Scoring and qualification** happen in the lead-qualification workflow, not in this skill.

> **Browser observation rule:** When inspecting any browser state (profiles, search results, menus, dialogs), always prefer **snapshot** (`browser_snapshot`) over screenshots. Only fall back to a screenshot if snapshot fails or is unavailable.

## Step 1 — Fetch leads from LinkedIn Sales Navigator

Open the following pre-filtered LinkedIn Sales Navigator URL directly in the browser:

```
https://www.linkedin.com/sales/search/people?query=(recentSearchParam%3A(id%3A4332039097%2CdoLogHistory%3Atrue)%2Cfilters%3AList((type%3ACOMPANY_HEADCOUNT%2Cvalues%3AList((id%3AB%2Ctext%3A1-10%2CselectionType%3AINCLUDED)%2C(id%3AC%2Ctext%3A11-50%2CselectionType%3AINCLUDED)%2C(id%3AA%2Ctext%3ASelf-employed%2CselectionType%3AINCLUDED)))%2C(type%3AINDUSTRY%2Cvalues%3AList((id%3A3100%2Ctext%3AMobile%2520Computing%2520Software%2520Products%2CselectionType%3AEXCLUDED)%2C(id%3A4%2Ctext%3ASoftware%2520Development%2CselectionType%3AEXCLUDED)%2C(id%3A3099%2Ctext%3AEmbedded%2520Software%2520Products%2CselectionType%3AEXCLUDED)%2C(id%3A3101%2Ctext%3ADesktop%2520Computing%2520Software%2520Products%2CselectionType%3AEXCLUDED)%2C(id%3A3102%2Ctext%3AIT%2520System%2520Custom%2520Software%2520Development%2CselectionType%3AEXCLUDED)%2C(id%3A3130%2Ctext%3AData%2520Security%2520Software%2520Products%2CselectionType%3AEXCLUDED)%2C(id%3A6%2Ctext%3ATechnology%252C%2520Information%2520and%2520Internet%2CselectionType%3AEXCLUDED)%2C(id%3A3231%2Ctext%3AInformation%2520Technology%2520%2526%2520Services%2CselectionType%3AEXCLUDED)%2C(id%3A96%2Ctext%3AIT%2520Services%2520and%2520IT%2520Consulting%2CselectionType%3AEXCLUDED)%2C(id%3A3106%2Ctext%3AIT%2520System%2520Data%2520Services%2CselectionType%3AEXCLUDED)%2C(id%3A1855%2Ctext%3AIT%2520System%2520Design%2520Services%2CselectionType%3AEXCLUDED)))%2C(type%3APOSTED_ON_LINKEDIN%2Cvalues%3AList((id%3ARPOL%2Ctext%3APosted%2520on%2520LinkedIn%2CselectionType%3AINCLUDED)))%2C(type%3ACURRENT_TITLE%2Cvalues%3AList((id%3A35%2Ctext%3AFounder%2CselectionType%3AINCLUDED)%2C(id%3A103%2Ctext%3ACo-Founder%2CselectionType%3AINCLUDED)%2C(id%3A1%2Ctext%3AOwner%2CselectionType%3AINCLUDED)%2C(id%3A195%2Ctext%3ACo-Owner%2CselectionType%3AINCLUDED)%2C(id%3A6%2Ctext%3APresident%2CselectionType%3AINCLUDED)))%2C(type%3AREGION%2Cvalues%3AList((id%3A103644278%2Ctext%3AUnited%2520States%2CselectionType%3AINCLUDED)%2C(id%3A101165590%2Ctext%3AUnited%2520Kingdom%2CselectionType%3AINCLUDED)%2C(id%3A101174742%2Ctext%3ACanada%2CselectionType%3AINCLUDED)%2C(id%3A101452733%2Ctext%3AAustralia%2CselectionType%3AINCLUDED)))%2C(type%3ALEAD_LIST%2Cvalues%3AList((id%3A7449361383735050240%2Ctext%3AAgent%2527s%2520Lead%2520List%2CselectionType%3AEXCLUDED%2Cicon%3Alist)))))&sessionId=XGDdjUi7RpGBGBjSafDLsQ%3D%3D
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

3. **Sourcing disqualification** — Before any connect or HubSpot step, evaluate the lead against the checks below using headline, About, company name/description, posts, services, and any visible positioning. **If any disqualifier clearly applies:**
   - **Save to Agent's Lead List** (Step 2a, save-only) so the lead is excluded from all future searches via the `LEAD_LIST` exclusion filter — this prevents the same disqualified profile from surfacing again.
   - Do **not** send a connection request.
   - Do **not** push to HubSpot.
   - Note the lead in the run summary under "Skipped at sourcing" with a one-line reason, then return to results.

### Disqualification (sourcing gate)

Disqualify (no HubSpot; skip connect) if the profile or company aligns with wrong-fit industries or positioning:

**Industry / business model**

- AI agencies  
- Automation consultants  
- Crypto / Web3  
- Enterprise organisations (targets or presents as vendor to large corp at scale)  
- Highly technical businesses (deep infra/eng-first shops where positioning is primarily technical execution, not marketing-led services you target)  
- “Make money online” / get-rich-quick operators  

**Signals on the profile**

- Sells AI services or lists AI offerings as core revenue  
- Heavily posts about AI (dominant topic vs occasional tool mention)  
- Positions as an automation expert (primary identity)  
- References prompts, agents, or workflows **heavily** as their core pitch  
- Already offers AI consulting  
- Has or advertises internal AI/automation teams (you’re competing with their in-house capability)  
- Reads as enterprise/corporate vendor (tone, clientele, procurement-style language)  
- Complex procurement structures apparent (RFx-only, gov/defense primes as primary GTM, etc.)  
- Already heavily systemised (sells packaged automation/AI ops as their product—you’re not the first mover in that stack)

**Ambiguity:** If it’s borderline, prefer **disqualifying** at sourcing (no HubSpot) and note “borderline — skipped” in the run summary.

4. Close the profile tab once extraction (and disqualification decision) is complete; if qualified, proceed to Step 2. If disqualified, return to the search results for the next lead.

## Step 2 — Save each lead to Agent's Lead List, then send a connection request

Use the **`linkedin-sales-nav-lead-actions`** skill and the Sales Navigator **lead URL** you captured (`https://www.linkedin.com/sales/lead/...`). Full CLI reference: [`workspace/skills/linkedin-sales-nav-lead-actions/SKILL.md`](../linkedin-sales-nav-lead-actions/SKILL.md).

### 2a — Save to list (every lead — qualified and disqualified)

**All leads** processed in Step 1 — regardless of disqualification outcome — must be saved to **Agent's Lead List**. This is what drives the `LEAD_LIST` exclusion filter in the search URL and prevents the same profile from reappearing in future runs.

1. **Preferred:** run the save action:

```bash
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --openclaw \
  --action save \
  --profile-url '<Sales Navigator lead URL>'
```

(`--list-name` defaults to **Agent's Lead List**; pass it explicitly if you use another list.)

2. **If the script fails** (e.g. `ok: false`, timeout, or broken selectors): fall back to the **`linkedin-sales-navigator`** browser flow — open the lead profile, click **Save** button, and choose **Agent's Lead List**.

**After saving a disqualified lead, stop here** — do not proceed to Step 2b or Step 3. Return to search results for the next lead.

### 2b — Connection request (qualified leads only, after save)

**Pick the outreach account (round-robin):**

1. Read `workspace/state/outreach_account.json`. If the file is missing or unreadable, treat `last_used` as `openclaw-2`.
2. Toggle: if `last_used` is `openclaw`, set `active_account = openclaw-2`; if it is `openclaw-2` (or anything else), set `active_account = openclaw`.
3. **Update state file** — write `{"last_used": "<active_account>"}` back to `workspace/state/outreach_account.json` immediately, before sending the connection request, so the slot is consumed even if the connect step fails.
4. Send the connection request using `--browser-profile <active_account>`.
5. Carry `active_account` forward to Step 3 for HubSpot.

Use browser profile `<active_account>` (`openclaw` or `openclaw-2`) for the connection request.

```bash
# <active_account> is the round-robin result from above (openclaw or openclaw-2).
# Default to openclaw if undetermined.
python3 workspace/skills/linkedin-sales-nav-lead-actions/scripts/linkedin_sales_nav_cli.py \
  --browser-profile <active_account> \
  --action connect \
  --profile-url '<Sales Navigator lead URL>' \
  --note "Optional invitation note."
```

If connect fails after a successful save, use browser automation (`openclaw browser --browser-profile <active_account>` → **⋯** next to Message → **Connect**) as a last resort, per **`linkedin-sales-nav-lead-actions`**.

This ensures every **qualified** processed lead is tracked in Sales Navigator and excluded from future searches (preventing duplicates via the `LEAD_LIST` exclusion filter in the URL).

## Step 3 — Push each lead into HubSpot as a Contact

For each **qualified** lead only (passed sourcing disqualification; never create contacts for disqualified profiles). Create a contact in HubSpot using the `hubspot` skill with these fields mapped:

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
| `active_account` from Step 2b                            | `outreach_account` — browser profile used to send the connection request (`openclaw` or `openclaw-2`); all downstream outreach skills route back to the same LinkedIn account using this value |

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
    "hs_lead_status": "NEW",
    "outreach_account": "<active_account from Step 2b — openclaw or openclaw-2>"
  }
}
```

**Ensure the `outreach_account` HubSpot property exists** (single-line text) before the first run — create it in HubSpot Settings → Properties → Contact properties if not already present.

**URL rules:** `hs_linkedin_url` must be the public profile link. `linkedin_sales_lead_url` must be the **Sales Navigator** page URL only — never put the SN URL into `hs_linkedin_url` (Apollo expects a normal `linkedin.com/in/...` or equivalent member URL).


## Step 4 — Report results

After finishing the run, show:

1. **Sourced (HubSpot)** — summary table for leads that cleared disqualification and were created:

   - Lead name, company, role, **profile URL** (`hs_linkedin_url`), **Sales Navigator lead URL**, email (or "N/A"), phone (or "N/A"), HubSpot contact ID returned from the API  

2. **Skipped at sourcing** — brief list of disqualified leads (name, company, one-line reason). No HubSpot ID.

If any **qualified** contact creation fails (e.g. duplicate email), note the error and continue with the next lead.

Once the summary table is complete, close all remaining browser tabs that were opened during this session (Sales Navigator search results tab and any residual profile tabs).

## Step 5 — Send sourced leads to Slack

After finishing sourcing and HubSpot pushes, send a Slack message listing **only leads added to HubSpot** in this run (name, company, and role). Optionally append a short “Skipped (disqualified): N” count or names if useful for the operator.

Use this command format:

```bash
openclaw message send --channel slack --target "channel:C0B0GAZ032L" --message "Sourced leads: <Lead 1 — Company — Role>; <Lead 2 — Company — Role>; ..."
```
