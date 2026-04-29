---
name: linkedin-sales-navigator
description: >-
  Open LinkedIn Sales Navigator and apply lead/account filters (agency type, keywords, titles,
  seniority, headcount, geography, spotlights) using the openclaw browser CLI (openclaw browser --browser-profile openclaw;
  open/navigate → snapshot → click/type/fill). Use when the user mentions LinkedIn Sales Navigator, Sales Nav,
  lead filtering, prospect search, agency pipeline, or wants to find leads/accounts with
  specific criteria on LinkedIn. Requires an active LinkedIn Sales Navigator session in the
  openclaw browser.
homepage: https://linkedin.com/sales
metadata:
  openclaw:
    emoji: 🎯
---

# LinkedIn Sales Navigator (`openclaw browser`)

Search and filter leads/accounts in **LinkedIn Sales Navigator** by driving the managed browser with the **`openclaw browser`** CLI (**always** `--browser-profile openclaw`): `open` / `navigate` → `snapshot` → `click` / `type` / `fill` — see workspace **`TOOLS.md`** for subcommand syntax and Sales Navigator compose tips.

**Docs**: [Browser](https://docs.openclaw.ai/tools/browser) · [Browser login](https://docs.openclaw.ai/tools/browser-login)

## Inputs (from the user or OpenClaw UI)

| Input | Required | Notes |
|-------|----------|-------|
| **Agency type** | Yes (preset) | Marketing, Web design, Creative, Growth — or "All" |
| **Geography** | Preset default | US, UK, Canada — override by typing in chat |
| **Headcount** | Preset default | 2–30 employees — override in chat |
| **Seniority / Title** | Preset default | Founder, Owner, Director — override in chat |
| **Active on LinkedIn** | Preset default | Posted in last 30 days — can disable |
| **Custom keywords** | Optional | Appended to agency keyword string |
| **Search type** | Optional | `people` (default) or `company` |

Do **not** ask for LinkedIn passwords; login happens in the browser window.

## Preconditions

1. **Gateway browser** enabled (see [Browser](https://docs.openclaw.ai/tools/browser)).
2. **LinkedIn Sales Navigator session**: user must be logged in on the **`openclaw`** profile with an active Sales Navigator subscription. If logged out, open the login URL and wait for the user to complete login/2FA before continuing.
3. **Subscription tier**: some filters (e.g. TeamLink, Intent) require Advanced/Advanced Plus — skip unavailable filters and notify the user.

## Agency Type → Keyword Mapping

When the user selects an agency type, inject the corresponding keyword string into the search bar:

| Agency Type | Keywords injected |
|-------------|------------------|
| Marketing agencies | `"marketing agency" OR "digital marketing" OR "marketing services"` |
| Web design agencies | `"web design" OR "web development agency" OR "website design"` |
| Creative agencies | `"creative agency" OR "creative studio" OR "branding agency"` |
| Growth agencies | `"growth agency" OR "growth marketing" OR "performance marketing"` |

**Multiple selections:** combine with `OR`:
```
"marketing agency" OR "digital marketing" OR "growth agency" OR "growth marketing"
```

## Preset: Agency Pipeline Engine (Phase 1)

Default criteria applied unless the user overrides a specific filter in chat:

| Filter | Value | Sales Navigator path |
|--------|-------|----------------------|
| Company headcount | 1–50 employees (1–10, 11–50) | All Filters → Company Headcount |
| Job title | Founder, Owner, Co-Founder, Director, Managing Director, CEO | All Filters → Current Job Title |
| Geography | United States, United Kingdom, Canada | All Filters → Geography |
| Active on LinkedIn | Posted on LinkedIn (last 30 days) | All Filters → Posted on LinkedIn |
| Lead List exclusion | Exclude "Agent's Lead List" | All Filters → Lead List → Excluded |

**Override rule:** any value the user provides in chat replaces only that filter; all other preset values remain active.

## Browser Automation Workflow

Two approaches are available — **prefer Method A (URL query param)** as it is faster and more reliable than clicking through the UI.

---

### Method A — Direct URL with Query Params (Preferred)

Build and navigate to a fully-parameterised Sales Navigator URL. LinkedIn encodes all filters in the `query=` param, so a single `open` call loads results with every filter already applied.

#### Step 1 — Start / ensure browser

```bash
openclaw browser --browser-profile openclaw status
openclaw browser --browser-profile openclaw start
```

#### Step 2 — Build the URL

Start from the base template and substitute the values for the user's request:

```
https://www.linkedin.com/sales/search/people?query=(spellCorrectionEnabled%3Atrue%2Cfilters%3AList({FILTERS})%2Ckeywords%3A{KEYWORDS})&viewAllFilters=true
```

**Filter building blocks** (URL-encoded, combine with `%2C` between filter entries):

| Filter | Encoded param fragment |
|--------|----------------------|
| Headcount: 1–10 | `(type%3ACOMPANY_HEADCOUNT%2Cvalues%3AList((id%3AB%2Ctext%3A1-10%2CselectionType%3AINCLUDED)%2C(id%3AC%2Ctext%3A11-50%2CselectionType%3AINCLUDED)))` |
| Title: Founder (35) | `(id%3A35%2Ctext%3AFounder%2CselectionType%3AINCLUDED)` |
| Title: Owner (1) | `(id%3A1%2Ctext%3AOwner%2CselectionType%3AINCLUDED)` |
| Title: Co-Founder (103) | `(id%3A103%2Ctext%3ACo-Founder%2CselectionType%3AINCLUDED)` |
| Title: Director (5) | `(id%3A5%2Ctext%3ADirector%2CselectionType%3AINCLUDED)` |
| Title: Managing Director (16) | `(id%3A16%2Ctext%3AManaging%2520Director%2CselectionType%3AINCLUDED)` |
| Title: CEO (8) | `(id%3A8%2Ctext%3AChief%2520Executive%2520Officer%2CselectionType%3AINCLUDED)` |
| Region: United States | `(id%3A103644278%2Ctext%3AUnited%2520States%2CselectionType%3AINCLUDED)` |
| Region: United Kingdom | `(id%3A101165590%2Ctext%3AUnited%2520Kingdom%2CselectionType%3AINCLUDED)` |
| Region: Canada | `(id%3A101174742%2Ctext%3ACanada%2CselectionType%3AINCLUDED)` |
| Region: Spain | `(id%3A105646813%2Ctext%3ASpain%2CselectionType%3AINCLUDED)` |
| Posted on LinkedIn | `(type%3APOSTED_ON_LINKEDIN%2Cvalues%3AList((id%3ARPOL%2Ctext%3APosted%2520on%2520LinkedIn%2CselectionType%3AINCLUDED)))` |
| Exclude Lead List | `(type%3ALEAD_LIST%2Cvalues%3AList((id%3A{LIST_ID}%2Ctext%3A{LIST_NAME}%2CselectionType%3AEXCLUDED)))` |

> **Note on `POSTED_ON_LINKEDIN`**: this is a **standalone filter type** (not nested under `SPOTLIGHT`). Use `type%3APOSTED_ON_LINKEDIN` with `id%3ARPOL`.

> **Note on `LEAD_LIST` exclusion**: replace `{LIST_ID}` with the numeric Sales Navigator list ID and `{LIST_NAME}` (URL-encoded) with the list name. The preset excludes the "Agent's Lead List" (`id%3A7449361383735050240%2Ctext%3AAgent%2527s%2520Lead%2520List`). Remove this block if the user has no list to exclude.

**Common region IDs:**

| Region | ID |
|--------|----|
| United States | `103644278` |
| United Kingdom | `101165590` |
| Canada | `101174742` |
| Spain | `105646813` |
| Australia | `101452733` |
| Germany | `101282230` |
| France | `105015875` |

**Keywords** — URL-encode the keyword string (spaces → `%2520`, quotes → `%2522`, `OR` stays literal):

```
%2522marketing%2520agency%2522%2520OR%2520%2522digital%2520marketing%2522%2520OR%2520%2522web%2520design%2522%2520OR%2520%2522web%2520development%2520agency%2522%2520OR%2520%2522creative%2520agency%2522%2520OR%2520%2522branding%2520agency%2522%2520OR%2520%2522growth%2520agency%2522%2520OR%2520%2522growth%2520marketing%2522%2520OR%2520%2522performance%2520marketing%2522
```

#### Step 3 — Directly open the built URL

**Default preset URL** (all agency types · US + UK + Canada · Founder/Owner/Co-Founder/Director/Managing Director/CEO · 1–50 headcount · posted on LinkedIn · excludes Agent's Lead List):

```bash
openclaw browser --browser-profile openclaw open "https://www.linkedin.com/sales/search/people?query=(spellCorrectionEnabled%3Atrue%2Cfilters%3AList((type%3ACOMPANY_HEADCOUNT%2Cvalues%3AList((id%3AB%2Ctext%3A1-10%2CselectionType%3AINCLUDED)%2C(id%3AC%2Ctext%3A11-50%2CselectionType%3AINCLUDED)))%2C(type%3ALEAD_LIST%2Cvalues%3AList((id%3A7449361383735050240%2Ctext%3AAgent%2527s%2520Lead%2520List%2CselectionType%3AEXCLUDED)))%2C(type%3AREGION%2Cvalues%3AList((id%3A103644278%2Ctext%3AUnited%2520States%2CselectionType%3AINCLUDED)%2C(id%3A101165590%2Ctext%3AUnited%2520Kingdom%2CselectionType%3AINCLUDED)%2C(id%3A101174742%2Ctext%3ACanada%2CselectionType%3AINCLUDED)))%2C(type%3ACURRENT_TITLE%2Cvalues%3AList((id%3A35%2Ctext%3AFounder%2CselectionType%3AINCLUDED)%2C(id%3A1%2Ctext%3AOwner%2CselectionType%3AINCLUDED)%2C(id%3A103%2Ctext%3ACo-Founder%2CselectionType%3AINCLUDED)%2C(id%3A5%2Ctext%3ADirector%2CselectionType%3AINCLUDED)%2C(id%3A16%2Ctext%3AManaging%2520Director%2CselectionType%3AINCLUDED)%2C(id%3A8%2Ctext%3AChief%2520Executive%2520Officer%2CselectionType%3AINCLUDED)))%2C(type%3APOSTED_ON_LINKEDIN%2Cvalues%3AList((id%3ARPOL%2Ctext%3APosted%2520on%2520LinkedIn%2CselectionType%3AINCLUDED))))%2Ckeywords%3A%2522marketing%2520agency%2522%2520OR%2520%2522digital%2520marketing%2522%2520OR%2520%2522web%2520design%2522%2520OR%2520%2522web%2520development%2520agency%2522%2520OR%2520%2522creative%2520agency%2522%2520OR%2520%2522branding%2520agency%2522%2520OR%2520%2522growth%2520agency%2522%2520OR%2520%2522growth%2520marketing%2522%2520OR%2520%2522performance%2520marketing%2522)"
```

When the user overrides geography, titles, or other filters, reconstruct the URL by swapping the relevant encoded param blocks before navigating. To remove the lead list exclusion (e.g. first run with no saved list), drop the entire `LEAD_LIST` filter block.

#### Step 4 — Snapshot & read results

1. **Re-snapshot** after the page loads.
2. Report the **total lead count** shown at the top.
3. Optionally list visible lead names/companies from the first page snapshot.

---

### Method B — Browser UI Automation (Fallback)

Use when URL construction fails or the user prefers interactive filtering.

#### Step 1 — Start / ensure browser

```bash
openclaw browser --browser-profile openclaw status
openclaw browser --browser-profile openclaw start
```

#### Step 2 — Navigate to Sales Navigator

For **people/lead** search (default):
```bash
openclaw browser --browser-profile openclaw open "https://www.linkedin.com/sales/search/people"
```

For **account/company** search:
```bash
openclaw browser --browser-profile openclaw open "https://www.linkedin.com/sales/search/company"
```

#### Step 3 — Snapshot & enter keywords

1. **Snapshot** the page to get current refs.
2. **Act**: click the search bar ref → type the agency keyword string.
3. Press Enter or click the search button ref.
4. **Re-snapshot** after results load.

#### Step 4 — Open All Filters

1. From the snapshot, locate the **"All filters"** button ref.
2. **Act**: click it → wait for the filter panel to open.
3. **Re-snapshot** to get filter panel refs.

#### Step 5 — Apply each filter

Work through each filter in order; re-snapshot between filter sections if refs change:

```
Company Headcount  → check "1-10" and "11-50"
Job Title          → type and select: Founder, Owner, Director
Seniority Level    → select: Owner, C-Level, Director
Geography          → type and select: United States, United Kingdom, Canada
Spotlights         → check: Posted on LinkedIn
```

For any filter the user overrode in chat, use their value instead of the preset.

#### Step 6 — Apply & read results

1. **Act**: click **"Show results"** / **"Apply"** button ref.
2. **Re-snapshot** after results load.
3. Read and **report the total lead count** shown at the top of results.
4. Optionally snapshot the first page of results and list visible lead names/companies.

#### Step 7 — Save to list (optional)

If the user wants to export or save leads:
1. Snapshot → locate **"Save to list"** or **"Create list"** button ref.
2. Act: click → name the list → save.
3. Remind the user that CSV export is available from **Lists** in the Sales Navigator left nav.

## CLI Quick Checks

```bash
# Check browser status
openclaw browser --browser-profile openclaw status

# Manual snapshot for debugging
openclaw browser --browser-profile openclaw snapshot
```

## Filter Cheatsheet

```
Keywords          → Search bar at top
Job Title         → All Filters → Job Title
Seniority         → All Filters → Seniority Level
Industry          → All Filters → Industry
Headcount         → All Filters → Company Headcount
Geography         → All Filters → Geography
Changed Jobs      → All Filters → Job Change (Spotlights)
Posted Recently   → All Filters → Posted on LinkedIn (Spotlights)
```

## Safety & Rate Limits

- **LinkedIn ToS**: automated filtering/scraping can violate terms; use for legitimate prospecting only.
- **Rate**: avoid rapid-fire navigation — space actions, re-snapshot before each act (~30 actions/hour guideline).
- Refs are **not stable** across page loads — always re-snapshot before clicking after a navigation.
- If Sales Navigator redirects to login, pause and ask the user to log in before resuming.

## Related

- **`linkedin`** skill: general LinkedIn browser patterns and login guidance.
- **`linkedin-message-browser`** skill: send DMs to leads found via this skill.
- **`lead-sourcing`** skill: saving and organizing sourced leads after filtering.
