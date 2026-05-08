---
name: lead-qualification
description: >-
  Run the HubSpot → Apollo → Sales Navigator qualification workflow: search for NEW contacts with
  a LinkedIn URL, enrich with Apollo (person + organization), complete mandatory Sales Navigator
  profile review and website visits, classify Agency / Business Owner / Disqualified using ICP and
  disqualification rules (operational-infrastructure fit—not AI positioning), score with the
  Agency (white label) or Business Owner (direct subscription) model (industry priority, geography,
  headcount 3–20 ideal, founder proximity, operational pain, revenue, maturity/clarity, responsiveness),
  persist lead_score and lead_score_details via HubSpot PATCH, and report. Use when the user wants
  to qualify leads, score NEW contacts, or move sourced contacts toward outreach. Requires hubspot,
  apollo-enrichment (apollo.py), and linkedin-sales-navigator (browser); active Sales Navigator session
  for Step 3.

metadata:
  openclaw:
    emoji: 📋
---

Use the `hubspot` skill, `apollo-enrichment` skill (`workspace/skills/apollo-enrichment/apollo.py` per [SKILL.md](../apollo-enrichment/SKILL.md)), and `linkedin-sales-navigator` (browser — required for Step 3) to **qualify leads**: classify type against ICP, enrich with Apollo (person + organization), **backfill missing HubSpot contact and company data from Apollo**, score with the correct model, and persist everything in HubSpot.

## Positioning and ICP (read before scoring)

**What you are selling:** Operational infrastructure for growing businesses—lead flow, follow-up, backend ops, communication, onboarding, operational support. **Do not** position or score as “an AI company”; AI-heavy positioning on the **lead’s** side is usually a **negative** signal.

**Ideal client**

- Founder-led, small team, operationally busy, growing quickly  
- Still handles too much manually; inconsistent systems; operational bottlenecks; weak backend infrastructure  
- **Sweet spot:** growth has outpaced operations  

**Ideal headcount band:** **3–20 employees** (scoring rewards this band highest).

**Strong-fit behaviors**

- Decisions quickly; founders still involved day-to-day  
- Reliant on referrals/leads; operational chaos behind growth; inconsistent follow-up; admin-heavy  
- Weak CRM/processes; already generating revenue; needs **structure more than strategy**

---

## Priority industries (Industry Priority row)

Map the lead’s **vertical** (Apollo industry, LinkedIn company description, website copy, job titles/services) to **one** tier for the **Industry Priority** criterion:

| Tier | Points | Examples / guidance |
|------|--------|---------------------|
| **High** | **+10** | Real estate agencies, buyer’s agents, property management; trades (roofing, electrical, plumbing, HVAC), construction, builders; recruitment agencies; mortgage/finance brokers; accounting firms; clinics (physio, chiro, dental), med spas, gyms; home services; commercial field services |
| **Medium** | **+5** | Branding/creative/web agencies, niche consultancies, marketing agencies, education/coaching businesses |
| **Low** | **0** | Ecommerce, SaaS, generic tech startups |
| **Negative** | **−10** | AI agencies, automation consultants, crypto/web3, enterprise/corporate procurement-heavy orgs, highly technical positioning, “make money online” operators |

If unclear between High and Medium, prefer evidence from **what they sell** and **who buys** (B2B services to local/SMB vs agency retainers to brands).

---

## Disqualification rules (apply before and during scoring)

**Disqualify** (classification **Disqualified**, score **0**, skip numeric models) when any of these are **clear and primary**:

- Sells AI services or AI consulting as core offer  
- Heavily posts about AI; positions as automation expert; prompt/agent/workflow influencer vibe  
- Already offers AI consulting or shows internal AI/automation team as main differentiator  
- Enterprise/corporate with complex procurement (not founder-accessible)  
- Spam, student-only, recruiter-only, or impossible to classify with reasonable confidence  

**Heavy penalty or disqualify** (if not fully Disqualified, drive **Operational Pain** and overall fit **down**—and consider Disqualified if overwhelming):

- Operational pain signals absent because they are **already heavily systemised** (strong ops/CRM/automation messaging across site + LinkedIn with no chaos signals)  

**Check evidence across:** LinkedIn profile, posts/content, website, service offering, company description.

---

## Sales pathways (two tracks)

| Lead type | What you sell them |
|-----------|-------------------|
| **Agency** | White label offering |
| **Business Owner** | Direct subscription |
| **Disqualified** | Do not sell — band \< 40 or explicit disqualification |

---

## Step 1 — Fetch contacts to qualify from HubSpot

Search for contacts that are **new / not yet qualified** for this pipeline. Use `hs_lead_status = NEW` (adjust if your portal uses a dedicated “Unqualified queue” property).

Use the [Search contacts API](https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/search/search-contacts):

```
POST https://api.hubapi.com/crm/v3/objects/contacts/search
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "filterGroups": [
    {
      "filters": [
        {
          "propertyName": "hs_lead_status",
          "operator": "EQ",
          "value": "NEW"
        },
        {
          "propertyName": "hs_linkedin_url",
          "operator": "HAS_PROPERTY"
        }
      ]
    }
  ],
  "properties": [
    "firstname",
    "lastname",
    "email",
    "company",
    "jobtitle",
    "hs_linkedin_url",
    "linkedin_sales_lead_url",
    "hs_lead_grade",
    "lead_score",
    "lead_score_details",
    "hs_lead_status",
    "country",
    "state",
    "city",
    "phone",
    "mobilephone"
  ],
  "sorts": ["createdate"],
  "limit": 5,
  "after": "0"
}
```

For each contact, capture: `id`, first/last name, company, job title, **`hs_linkedin_url`** (public profile — **use for Apollo**), **`linkedin_sales_lead_url`** (Sales Navigator lead page), email, phone, and any HubSpot location fields — baseline to compare against Apollo so you only **fill gaps** on the contact and on the linked **company** (domain / website / industry live on the **company** object; fetch or create that record during backfill — see below).

---

## Step 2 — Enrich with Apollo (person + organization)

Use **`APOLLO_API_KEY`** and the bundled script from the apollo-enrichment skill directory:

```bash
cd workspace/skills/apollo-enrichment

# Person match — use public profile URL only (hs_linkedin_url)
python3 apollo.py enrich --linkedin "<hs_linkedin_url_public_profile>" --json

# If you have work email from HubSpot, also try:
python3 apollo.py enrich --email "<email>" --json

# Organization enrich — use primary_domain (or website host) from Apollo person.organization
python3 apollo.py company --domain "<org_primary_domain>" --json
```

From Apollo **person** JSON, extract at least: name, title, headline, email, phone, city/state/country, public LinkedIn profile URL, and `organization` (name, `primary_domain`, `estimated_num_employees`, industry, short description, technologies, etc.).

From Apollo **organization** JSON, extract: domain, industry, employee estimates, description — use with LinkedIn + site to assign **Industry Priority**, **Company Size**, and **Business maturity** (Business Owner) where LinkedIn alone is thin.

### Backfill HubSpot from Apollo (required)

After Step 2, **push missing data to HubSpot** so the CRM matches what Apollo returned. Compare each field to what you fetched in Step 1 (and any associated company). **Fill empty or placeholder values**; do not blindly overwrite good HubSpot data unless Apollo is clearly more accurate (e.g. legal org name, corrected domain).

**On the contact (PATCH same `contact_id`):** map Apollo **person** (and nested `organization` where the contact field is really “current employer”) when HubSpot is missing or weak:

| HubSpot (typical) | Apollo source |
|-------------------|----------------|
| `email` | Work email from person (use `--reveal-email` only if your Apollo plan and policy allow it and Step 1 had no usable email) |
| `phone` / `mobilephone` | Direct / mobile from person |
| `jobtitle` | Current title |
| `firstname` / `lastname` | Parsed name if HubSpot name is blank |
| `company` | `organization.name` when company text is empty |
| `city` / `state` / `country` | Person location (consistent with geography in Step 5) |

**Website and organization on the company record:** HubSpot’s **company** object usually owns `domain`, `website`, `industry`, `numberofemployees`, and description-style fields. Using the [HubSpot skill](../hubspot/SKILL.md):

1. Resolve or create the **company** by Apollo `primary_domain` / org domain (search companies by `domain`, or create if none).
2. PATCH the company with missing **`domain`**, **`website`** (use org URL from Apollo, or `https://<primary_domain>` when only domain is known), **`name`**, **`industry`**, **`numberofemployees`** (map Apollo employee estimate to the format your property expects), and **description** / long-text fields if empty.
3. **Associate** the contact to that company (contact ↔ company) if the association is missing.

If your portal uses **custom properties** for Apollo-backed fields (e.g. org domain, employee band, Apollo IDs), set those too when empty. If a field does not exist in your portal, skip it rather than failing the run — note skipped mappings in `lead_score_details` (e.g. under a `HubSpot / mapping notes:` line).

If Apollo returns no person, still attempt `company` using a domain inferred from the contact’s company name (only if reliable); document gaps in `lead_score_details`.

**When Apollo is insufficient — treat as “Apollo off” for scoring inputs**

If any of the following is true, treat Apollo as off for those scoring inputs and use **only Step 3 + HubSpot** for the signals Apollo would normally supply (org size, industry, maturity, etc.). Step 3 is mandatory for every contact regardless; when Apollo is insufficient it must **fully substitute** for Apollo data:

- Apollo CLI errors (auth, rate limit, 5xx), timeout, or empty / `null` person match  
- Person match exists but **no usable `organization`** (no domain, no employee estimate, no description)  
- `company` enrich fails or returns no organization  

In that case, note in the qualification block: `Apollo: unavailable or partial — scored from Sales Navigator profile + website`.

---

## Step 3 — LinkedIn Sales Navigator profile + website (browser)

**Mandatory for every contact:** complete the full Sales Navigator profile review **and** the website visits below—do not skip because Apollo returned data. Use Apollo as a cross-check. This step is where you **detect disqualifiers** (AI/automation positioning), **founder proximity**, **operational pain**, and **industry** evidence.

1. **Open the lead** in Sales Navigator using **`linkedin_sales_lead_url`** if present; otherwise open **`hs_linkedin_url`**.
2. From the **Sales Navigator lead profile** (and linked company panel), capture:
   - Headline, About, current role, company name, **employee range** if shown, location / geography  
   - Recent posts and engagement — **scan for AI/automation selling, prompt/agent workflow hype, enterprise-only tone**  
   - Language that implies **agency** (clients, retainers, “we help brands”, services roster) vs **business owner** (single operating company, local/trade/clinic/service business)  
   - **Founder proximity:** named founder on site/branding, founder posting personally, founder in sales/content  
   - **Operational pain:** hiring admin/sales/Ops, “swamped”, inconsistent follow-up, manual/backend complaints, growth strain, messy CRM, disconnected tools  
   - **Heavily systemised signal:** strong “fully automated”, mature ops stack marketed as finished — penalise operational pain / fit per disqualification rules  
   - **Any website URL** on the profile or company card  
   - Open the **company Page** when possible (About, Posts, **Jobs**). Count **open roles**; note admin/sales/ops hiring vs only senior IC  
3. **Website visit:** For each distinct external site linked from the profile (prioritize the **company website**), open it in a **new tab**, confirm it loads, and assess **offer clarity**, **founder visibility**, **social proof / maturity**, **revenue structure** (packages, retainers, booking), and **fit vs negative ICP** (AI agency, automation consultant, enterprise). Close site tabs when done.

   **Optional public-web research helpers:** If needed, use `web_search` and public page fetches for evidence. Cite what you used in `lead_score_details`. Do not use private/authenticated content.

   **Website analysis (required per site — summarize under that URL in `lead_score_details`):** Beyond scoring tiers, record briefly:

   | Dimension | What to record |
   |-----------|----------------|
   | **Speed** | Perceived load (snappy vs sluggish); optional Lighthouse/PageSpeed headline |
   | **Mobile responsiveness** | Narrow viewport: readable, usable nav/CTAs |
   | **SEO** | Title/meta/H1 sanity; obvious gaps |
   | **E-commerce** | Cart/checkout vs brochure/service site (note **N/A** if not commerce) |
   | **Overall aesthetic** | Modern vs dated; cohesion |

   These notes **support** Service clarity, maturity, and “professional front vs chaotic ops” judgment; they do not replace founder/industry/pain evidence.

4. Use this evidence to fill **every scoring row** that lacks Apollo data. If unknown after profile + site, use the rubric **0** / **Unclear** tier and say so in the breakdown.
5. Close the profile tab when finished.

---

## Step 4 — Classify lead type (before scoring)

Every lead must be classified **before** applying points.

| Classification | Definition | Examples |
|----------------|------------|----------|
| **Agency** | Service business selling services to **clients** (white label pathway) | Branding/creative/web agencies, recruitment firms, marketing agencies, niche consultancies |
| **Business Owner** | **Non-agency** operating company (direct subscription pathway) | Trades, construction, real estate, clinics, gyms, professional/home/commercial services, accounting practices |
| **Disqualified** | Outside ICP, negative tier primary business, or DQ rules above | AI agencies, automation consultants, enterprise procurement-only, crypto/web3 core, spam/low-quality |

If **Disqualified**, set score to **`0`**, skip Step 5 models, set band **Disqualified**, and still PATCH HubSpot (see Step 7).

---

## Step 5 — Apply the correct scoring model (max 100)

Use **exactly one** model per contact. **Compute the sum of all rows; clamp `lead_score` to the range 0–100** if arithmetic yields a value outside that range (e.g. rare edge cases). Industry Priority may be **−10**, which pulls the total down.

### Geography (both models)

| Tier | Points |
|------|--------|
| USA | **10** |
| Australia | **8** |
| UK | **6** |
| Canada | **5** |
| Other | **0** |

Prefer contact **country** from HubSpot, then Apollo person country, then org HQ / profile location.

### Company size — employees (both models)

Use Apollo `estimated_num_employees` + LinkedIn company hints + website/careers; if unknown, **0 for this row** and say so.

| Band | Points |
|------|--------|
| **3–20** | **15** |
| **2** | **10** |
| **20–30** | **5** |
| **1** | **0** |
| **30+** | **0** |

### A. Agency scoring model (white label) — total 100

**Only if classified Agency.**

| # | Criterion | Max | Tiers / notes |
|---|-----------|-----|----------------|
| 1 | **Lead type** | **10** | Agency → **10** (only this model applies) |
| 2 | **Industry Priority** | **10** | High **+10**, Medium **+5**, Low **0**, Negative **−10** (see industry table) |
| 3 | **Geography** | **10** | See geography table |
| 4 | **Company size** | **15** | See company size table |
| 5 | **Founder proximity** | **15** | Highly visible / involved **15**; somewhat **8**; corporate / invisible **0** |
| 6 | **Operational pain signals** | **20** | Clear pressure **20**; some **10**; none obvious **0** |
| 7 | **Revenue indicators** | **10** | Retainers / multiple active clients **10**; some client work **5**; unclear **0** |
| 8 | **Service clarity** | **5** | Clear niche **5**; generalist **2**; unclear **0** |
| 9 | **Responsiveness signals** | **5** | Founder-accessible / direct **5**; some gatekeeping **2**; corporate process **0** |

**Founder proximity — evidence**

- **High:** Founder posts personally; visible on website/About; involved in sales or content; founder-led branding obvious  
- **Somewhat:** Founder named but low visibility; occasional presence  
- **Low/corporate:** No identifiable founder; generic corporate voice only  

**Operational pain — evidence (Agency)**

- **Clear:** Hiring admin/sales/support; inconsistent marketing; rapid growth narrative; bottlenecks; disconnected systems; messy backend / CRM chaos signals  
- **Some:** One weak signal (single hire, vague “busy”)  
- **None:** Quiet ops, no growth strain, or **already heavily systemised** with no chaos  

**Revenue indicators**

- **Strong:** Retainers, multiple active clients, packages, ongoing/recurring service language  
- **Some:** Clear client work without structure  
- **Unclear:** Cannot infer  

---

### B. Business Owner scoring model (direct subscription) — total 100

**Only if classified Business Owner.**

| # | Criterion | Max | Tiers / notes |
|---|-----------|-----|----------------|
| 1 | **Industry Priority** | **10** | High **+10**, Medium **+5**, Low **0**, Negative **−10** |
| 2 | **Geography** | **10** | See geography table |
| 3 | **Company size** | **15** | See company size table |
| 4 | **Founder proximity** | **20** | Highly visible **20**; somewhat **10**; corporate / invisible **0** |
| 5 | **Operational pain signals** | **25** | Clear **25**; some **12**; none **0** |
| 6 | **Revenue indicators** | **10** | Clear revenue / structured offering **10**; some **5**; unclear **0** |
| 7 | **Business maturity** | **5** | Established + testimonials/proof **5**; some proof **2**; none **0** |
| 8 | **Responsiveness signals** | **5** | Founder-accessible **5**; some gatekeeping **2**; corporate **0** |

**Operational pain — evidence (Business Owner)**

- **Clear:** Hiring staff; slow/manual processes; inconsistent follow-up; multiple service lines straining ops; growth strain; overload; poor backend systems; active but inconsistent marketing  
- **Some:** One or two medium signals  
- **None:** No strain or already highly systemised end-to-end  

**Business maturity**

- **Established:** Testimonials, reviews, case-style proof, years in business signals  
- **Some:** Sparse proof  
- **None:** No proof  

In `lead_score_details`, each scoring row must include **why** those points were assigned: cite tier + **evidence** (URLs, post themes, job counts, founder visibility). Tie website notes to clarity/maturity where relevant.

---

## Step 6 — Priority bands

| Score | Band |
|-------|------|
| **80–100** | **High Priority** |
| **60–79** | **Medium Priority** |
| **40–59** | **Low Priority** |
| **\< 40** | **Disqualified** |

If the math yields **\< 40** on a classified Agency/Business Owner lead, treat the **priority band** as Disqualified (you may keep the raw sum in `lead_score_details` for audit).

**High-priority lead characteristics (qualitative check)**

Founder-led; **3–20** staff; operationally stretched; manual/inconsistent systems; growing quickly; weak backend; responsive/decisive; traditional ops behind a strong front—**operational chaos behind growth**.

---

## Step 7 — Persist in HubSpot (company + contact)

Apply the **Apollo backfill** (Step 2) if you have not already done it this run: **company** create/search/PATCH and contact ↔ company **associate** when domain or org fields are missing, then **PATCH the contact** with qualification fields plus any remaining contact-level gaps (email, phone, title, location, `company` text).

Update the contact:

```
PATCH https://api.hubapi.com/crm/v3/objects/contacts/<contact_id>
Authorization: Bearer $HUBSPOT_ACCESS_TOKEN
Content-Type: application/json

{
  "properties": {
    "firstname": "<First Name>",
    "lastname": "<Last Name>",
    "company": "<Company Name>",
    "email": "<Email — set from Apollo when HubSpot was missing; omit if still unknown>",
    "phone": "<From Apollo if missing on contact>",
    "jobtitle": "<Role>",
    "hs_linkedin_url": "<Public LinkedIn profile URL — use for Apollo>",
    "linkedin_sales_lead_url": "<Sales Navigator lead URL from address bar>",
    "lead_score": "<0–100 — total score from Step 5; use string for HubSpot number field>",
    "lead_score_details": "<multi-line — see below>",
    "hs_lead_status": "IN_PROGRESS"
  }
}
```

**`lead_score` and `lead_score_details` (required custom contact properties):**

- **`lead_score`:** Set to the **final total** from Step 5 (0–100). For **Disqualified**, use **`0`**. Use the value HubSpot expects for your number property (typically a string in the API, e.g. `"72"`).
- **`lead_score_details`:** Multi-line text: run header, **every scoring row** for the model used with points + reasoning, data-source audit. **Do not omit scoring rows.**

**Suggested structure (in order):**

```
--- QUALIFICATION <ISO date> ---
Positioning check: Operational infrastructure fit | Not positioning lead as AI vendor (Y/N + note)
Pathway: Agency | White label OR Business Owner | Direct subscription OR Disqualified
Classification: Agency | Business Owner | Disqualified
Model used: Agency (100) | Business Owner (100) | N/A
Score: <n>/100 | Band: High | Medium | Low | Disqualified
Disqualifiers checked: <LinkedIn / posts / site — AI-automation-enterprise signals found or none>

[Scoring — each line: label, points, reasoning]

Data sources: Apollo OK | Apollo unavailable or partial — Sales Navigator + website
Apollo person summary: <1-3 lines, or "N/A — see LinkedIn/website notes">
Apollo org summary: <1-3 lines, or "N/A — see LinkedIn/website notes">
LinkedIn / Sales Navigator: <activity, founder, pain, hiring>
Websites reviewed: <each URL + compact Speed | Mobile | SEO | E-commerce | Aesthetic>
```

**Agency model — include all 9 rows:**

```
Lead type (Agency): <n> — …
Industry Priority: <n> — High/Medium/Low/Negative + why
Geography: <n> — …
Company size: <n> — band + evidence
Founder proximity: <n> — tier + evidence
Operational pain signals: <n> — tier + evidence
Revenue indicators: <n> — …
Service clarity: <n> — …
Responsiveness signals: <n> — …
```

**Business Owner model — include all 8 rows:**

```
Industry Priority: <n> — …
Geography: <n> — …
Company size: <n> — …
Founder proximity: <n> — …
Operational pain signals: <n> — …
Revenue indicators: <n> — …
Business maturity: <n> — …
Responsiveness signals: <n> — …
```

Filled example (Agency — abbreviated):

```
--- QUALIFICATION 2026-05-08 ---
Positioning check: Fit — trades-adjacent agency; lead does not sell AI tooling.
Pathway: Agency | White label
Classification: Agency
Model used: Agency (100)
Score: 76/100 | Band: Medium Priority
Disqualifiers checked: No AI/agency-automation positioning; SMB founder tone.

Lead type (Agency): 10 — Retainer positioning to external clients.
Industry Priority: 5 — Creative/marketing-adjacent studio → Medium tier.
Geography: 10 — US contact + HQ.
Company size: 15 — ~8 FTE (Apollo + LinkedIn).
Founder proximity: 15 — Founder in headline; posts 2×/week.
Operational pain signals: 10 — Hiring junior PM; posts about project overload.
Revenue indicators: 5 — Client logos; no explicit retainer copy.
Service clarity: 2 — Broad “creative partner” positioning.
Responsiveness signals: 5 — Book-a-call CTA; founder email tone on site.

Data sources: Apollo OK
Apollo person summary: …
Apollo org summary: …
LinkedIn / Sales Navigator: …
Websites reviewed: https://example.com — service site; Speed: OK | Mobile: OK | SEO: basic | E-commerce: N/A | Aesthetic: contemporary.
```

For **Disqualified**, lead with **`Disqualified: <reason>`**, set **`lead_score`** to **`0`**, and document DQ evidence from Step 3.

**`hs_lead_status` rules**

- **Disqualified** (explicit DQ or band \< 40): **`UNQUALIFIED`** if present in portal; else `NEW` with band explicit in details  
- **Qualified** (≥ 40): **`IN_PROGRESS`** for outreach pickup  

If your HubSpot has **custom properties** (e.g. `sales_pathway`, `priority_band`), fill them too.

---

## Step 8 — Report

Output a table:

| Name | Company | Classification | Pathway | Score (`lead_score`) | Band | HubSpot updated |
|------|---------|----------------|---------|----------------------|------|-----------------|

If PATCH fails, record the error and continue with the next contact.

---

## Step 9 — Send Slack alert for high-intent qualified leads

After reporting, send a Slack notification for each lead where **`lead_score` ≥ 80** (High Priority band).

**Trigger:** `lead_score` **≥ 80**.

```bash
openclaw message send --channel slack --target "channel:C0B0GAZ032L" --message "MESSAGE"
```

**Message requirements**

- Header: `MOSTLY — Lead Qualified - <lead_score> Score`  
- Name, Company, Conversation summary, LinkedIn profile link  

**Template:**

```text
MOSTLY — Lead Qualified <lead_score>
Name: <firstname lastname>
Company: <company>
Conversation summary: <1–3 sentences from qualification / operational fit>
LinkedIn profile link: <hs_linkedin_url>
```

If Slack send fails, log the failure and continue.
