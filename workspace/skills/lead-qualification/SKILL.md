---
name: lead-qualification
description: >-
  Run the HubSpot → Apollo → Sales Navigator qualification workflow: search for NEW contacts with
  a LinkedIn URL, enrich with Apollo (person + organization), complete mandatory Sales Navigator
  profile review and website visits (Speed, mobile, SEO, e-commerce, aesthetic), classify Agency / Business Owner / Disqualified, score with
  the correct model, persist lead_score and lead_score_details (full reasoning + audit context) via
  HubSpot PATCH, and
  report the summary table. Use when the user wants to qualify leads, score NEW contacts, or move
  sourced contacts toward outreach. Requires hubspot, apollo-enrichment (apollo.py), and
  linkedin-sales-navigator (browser); active Sales Navigator session for Step 3.

metadata:
  openclaw:
    emoji: 📋
---
Use the `hubspot` skill, `apollo-enrichment` skill (`workspace/skills/apollo-enrichment/apollo.py` per [SKILL.md](../skills/apollo-enrichment/SKILL.md)), and `linkedin-sales-navigator` (browser — required for Step 3) to **qualify leads**: classify type, enrich with Apollo (person + organization), **backfill missing HubSpot contact and company data from Apollo**, score with the correct model, and persist everything in HubSpot.

## Sales pathways (two tracks)

| Lead type       | What you sell them      |
|----------------|-------------------------|
| **Agency**     | White label offering    |
| **Business Owner** | Direct subscription |
| **Disqualified** | Do not sell — score band \< 40 or explicit disqualification |

---

## Step 1 — Fetch contacts to qualify from HubSpot

Search for contacts that are **new / not yet qualified** for this pipeline. Use `hs_lead_status = NEW` (adjust if your portal uses a dedicated “Unqualified queue” property).

Use the [Search contacts API](https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/search/search-contacts):

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


For each contact, capture: `id`, first/last name, company, job title, **`hs_linkedin_url`** (public profile — **use for Apollo**), **`linkedin_sales_lead_url`** (Sales Navigator lead page), email, phone, and any HubSpot location fields — these are the baseline to compare against Apollo so you only **fill gaps** on the contact and on the linked **company** (domain / website / industry live on the **company** object; fetch or create that record during backfill — see below).

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

From Apollo **organization** JSON, extract: domain, industry, employee estimates, revenue/funding hints, description, tech stack — use these to inform **website quality**, **revenue indicators**, and **business maturity** where LinkedIn alone is thin.

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

**Website and organization on the company record:** HubSpot’s **company** object usually owns `domain`, `website`, `industry`, `numberofemployees`, and description-style fields. Using the [HubSpot skill](../skills/hubspot/SKILL.md):

1. Resolve or create the **company** by Apollo `primary_domain` / org domain (search companies by `domain`, or create if none).
2. PATCH the company with missing **`domain`**, **`website`** (use org URL from Apollo, or `https://<primary_domain>` when only domain is known), **`name`**, **`industry`**, **`numberofemployees`** (map Apollo employee estimate to the format your property expects), and **description** / long-text fields if empty.
3. **Associate** the contact to that company (contact ↔ company) if the association is missing.

If your portal uses **custom properties** for Apollo-backed fields (e.g. org domain, employee band, Apollo IDs), set those too when empty. If a field does not exist in your portal, skip it rather than failing the run — note skipped mappings in `lead_score_details` (e.g. under a `HubSpot / mapping notes:` line).

If Apollo returns no person, still attempt `company` using a domain inferred from the contact’s company name (only if reliable); document gaps in `lead_score_details`.

**When Apollo is insufficient — treat as “Apollo off” for scoring inputs**

If any of the following is true, treat Apollo as off for those scoring inputs and use **only Step 3 + HubSpot** for the signals Apollo would normally supply (org size, industry, maturity, website quality, etc.). Step 3 is mandatory for every contact regardless; when Apollo is insufficient it must **fully substitute** for Apollo data:

- Apollo CLI errors (auth, rate limit, 5xx), timeout, or empty / `null` person match
- Person match exists but **no usable `organization`** (no domain, no employee estimate, no description)
- `company` enrich fails or returns no organization

In that case, note in the qualification block: `Apollo: unavailable or partial — scored from Sales Navigator profile + website`.

---

## Step 3 — LinkedIn Sales Navigator profile + website (browser)

**Mandatory for every contact:** complete the full Sales Navigator profile review **and** the website visits below—do not skip or shorten this step because Apollo returned data; use Apollo as a cross-check when it is available. When Apollo failed or is partial (see Step 2), extract everything you can from the profile and the web so those rows can still be scored.

1. **Open the lead** in Sales Navigator using **`linkedin_sales_lead_url`** if present; otherwise open **`hs_linkedin_url`**.
2. From the **Sales Navigator lead profile** (and linked company panel if shown), capture:
   - Headline, About, current role, company name, **employee range** if shown, location / geography
   - Recent posts and engagement (**LinkedIn activity** for scoring)
   - Language that implies **agency** (clients, retainers, “we help brands”, services roster) vs **business owner** (single operating company, product, local service)
   - **Any website URL** on the profile or company card (company site, Linktree, portfolio, “Visit website”)
   - For **Step 5** (website, maturity, revenue, pain): open the **company Page** from the panel when possible (About, Posts, **Jobs** / hiring). Count **open job posts** and note **scaling** language; apply the **Agency rows 5–8 metrics** (and the same evidence rules for Business Owner rows 3–6) in Step 5.
3. **Website visit:** For each distinct external site linked from the profile (prioritize the **company website**), open it in a **new tab**, confirm it loads, and assess **website quality**, **service clarity**, **business maturity** (case studies / testimonials), and **revenue / offer structure** (packages, pricing, “our clients”, retainers). Close site tabs when done.

   **Optional public-web research helpers:** If needed, you may use `web_search` to discover public sources (official site pages, company profiles, public job pages, press, reviews) and use web content fetching tools to read **public website content** for evidence. Use these only for public pages, cite what you used in `lead_score_details`, and do not use private/authenticated content.

   **Website analysis (required per site — summarize under that URL in `lead_score_details`):** Beyond the rubric used for scoring, explicitly assess each company site (and any distinct service URL you opened) on:

   | Dimension | What to record |
   |-----------|----------------|
   | **Speed** | Perceived cold-load performance (snappy vs sluggish first paint); obvious issues (long blank screen, huge hero media, blocking interstitial); if you use tooling (PageSpeed Insights, Lighthouse, or network tab in devtools), note **one headline** (e.g. “Lighthouse performance ~45 mobile” or “many large images”) — tooling is **optional**, observation is **required**. |
   | **Mobile responsiveness** | Resize to a narrow viewport (or device mode): readable text without horizontal scroll, tap targets and nav usable, CTAs not clipped; flag fixed-width or broken layouts. |
   | **SEO** | `<title>` / meta description quality (view source or inspector), logical H1 and heading hierarchy on key pages, indexable-looking URLs (not all hash-only), presence of **blog/help** or **sitemap** / `robots` hints if obvious; obvious gaps (duplicate empty titles, missing meta, thin doorway pages). |
   | **E-commerce capabilities** | Whether they **sell online** (cart, checkout, product catalog, “add to bag”, subscriptions). Note platform hints if visible (Shopify, WooCommerce, Stripe Checkout, Snipcart, etc.), B2B quote-only vs self-serve checkout, internationalization (currency/shipping). If **not** commerce, state **N/A — service/marketing site** (or brochure-only). |
   | **Overall modern aesthetic** | Visual and UX currency: typography, spacing, imagery quality, consistent components vs dated template; accessibility basics (contrast, focus states) if noticeable without deep audit. |

   Keep each dimension to **one short sentence** per URL unless a severe issue needs a second line. These notes **inform** Step 5 “Website quality” and related rows but do not replace the Step 5 point math.

4. Use this evidence to fill **every scoring row** that lacks Apollo data (company size, geography, website quality, maturity, revenue indicators, pain signals, service clarity). If a value is still unknown after profile + site review, use the rubric’s **0** or **Unclear** tier and say so in the score breakdown.
5. Close the profile tab when finished.

---

## Step 4 — Classify lead type (before scoring)

Each contact gets exactly one bucket:

| Classification   | Definition |
|------------------|------------|
| **Agency**       | Service-based business selling services to clients (agency, studio, consultancy positioning). **White label** pathway. |
| **Business Owner** | Operating company that is **not** primarily an agency selling to clients’ brands (e.g. product, local business, in-house brand). **Direct subscription** pathway. |
| **Disqualified** | Wrong ICP, spam, student, recruiter-only, competitor, or impossible to classify with reasonable confidence. |

If **Disqualified**, set score to `0`, skip the numeric models below, set priority band to **Disqualified**, and still PATCH HubSpot (see Step 7).

---

## Step 5 — Apply the correct scoring model (max 100)

Use **only one** model per contact.

### A. Agency scoring model (white label) — total 100

**Only if classified Agency.**

| # | Criterion | Points |
|---|-----------|--------|
| 1 | Lead type | Agency → **20**; otherwise use Business Owner model |
| 2 | Geography | United States **15**, Australia **13**, UK **10**, Canada **8**, Other **0** |
| 3 | Company size (employees) | 5–20 **10**, 2–5 **7**, 20–30 **5**, 1 **0** (use Apollo `estimated_num_employees` + LinkedIn; if unknown, treat as Other band **0** for this row) |
| 4 | LinkedIn activity | Active (weekly post/engagement) **10**, Semi-active **5**, Inactive **0** |
| 5 | Website quality | High / clear offer **10**, Basic **5**, Poor/none **0** |
| 6 | Business maturity | Case studies/testimonials **10**, Limited **5**, None **0** |
| 7 | Revenue indicators | Retainers / multiple clients **10**, Some client work **5**, Unclear **0** |
| 8 | Pain / need signals | Hiring/scaling **10**, Some **5**, None **0** |
| 9 | Service clarity | Clear niche **5**, Generalist **2**, Unclear **0** |

**Metrics for rows 5–8 (Agency) — Step 3 website visit + LinkedIn company Page + jobs**

Evidence must come from what you **actually opened**: the **company website** (and any distinct service URLs from the profile), the **LinkedIn company Page** from Sales Navigator (company panel / “View company” — About, Posts, Jobs if visible), and **LinkedIn job posts** for that company when available. Apollo org data can **support** but does not replace visiting site + company presence.

| # | Criterion | **High / full points tier — count toward “High” when enough signals match** | **Basic / middle tier** | **Low / zero tier** |
|---|-----------|-----------------------------------------------------------------------------|-------------------------|---------------------|
| **5** | **Website quality** | Treat as **High (10)** when **≥4** of: loads without error; HTTPS; clear primary navigation; services or offer explained above the fold; credible visuals/typography; working contact or booking CTA; mobile usable; no major broken flows. **Or** a polished portfolio + clear “what we sell” in one scroll. **Count Step 3 website-analysis signals where they strengthen this row:** strong **speed** perception, **mobile** layout clean at narrow width, **SEO** basics solid on homepage, **e-commerce** flows professional when applicable, **modern aesthetic** cohesive — any of these can substitute for one of the classic bullets when clearly evidenced. | **Basic (5):** Site exists but template-y, thin copy, vague services, one-page placeholder, or only a Linktree-style hub with weak business detail. **Or** several of speed / mobile / SEO / aesthetic are weak but the site still communicates an offer. | **Poor/none (0):** No company site, domain parking, 404/timeout, unrelated site, or you could not verify a real business site after Step 3. |
| **6** | **Business maturity** | **High (10):** **≥2** strong proof signals across **website + LinkedIn company**: named client logos or case studies, dated testimonials, project galleries, press/awards, detailed team/credentials **or** company Page posts that showcase deliverables (before/after, campaign results, client shout-outs). | **Limited (5):** Exactly **1** weak signal (e.g. generic “trusted by brands” with no names, single anonymous quote, sparse portfolio). | **None (0):** No client proof on site **and** nothing on the company Page that shows shipped work for clients. |
| **7** | **Revenue indicators** | **High (10):** **≥2** signals from **website and/or company LinkedIn**: retainers or packages, pricing or “starting at”, clear service tiers, “book strategy / discovery”, multiple named client types, “ongoing” / subscription language for services, or explicit fractional/interim positioning tied to revenue. | **Some (5):** Clear they serve clients but **no** explicit commercial structure (no packages, pricing, or retainer language). | **Unclear (0):** Cannot infer how they sell or monetize from site + company profile. |
| **8** | **Pain / need signals** | **High (10):** **Hiring / scaling:** **≥2** live **company job posts** (LinkedIn Jobs or careers page linked from site) in delivery, sales, growth, ops, or PM — **or** strong scaling narrative in **company Page posts** or About (headcount growth, new office, “we’re growing the team”) in roughly the **last 60 days**. Count **open roles** when you can see them. | **Some (5):** **1** open role **or** older/weaker hiring mention, or personal lead post about workload without company-level hiring. | **None (0):** No job posts and no credible scaling/hiring pressure from company Page or site. |

In `lead_score_details`, each scoring row must include **why** those points were assigned: cite the rubric tier you used and the **evidence** (e.g. geography source, employee band + where seen, activity frequency, site signals counted for website quality — **tie website quality to Step 3’s Speed / Mobile / SEO / E-commerce / Aesthetic notes when relevant**). One or two sentences per criterion is typical; avoid vague scores with no reasoning.

### B. Business Owner scoring model (direct subscription) — total 100

**Only if classified Business Owner.**

| # | Criterion | Points |
|---|-----------|--------|
| 1 | Geography | United States **15**, Australia **13**, UK **10**, Canada **8**, Other **0** |
| 2 | Company size | 5–20 **10**, 2–5 **7**, 20–30 **5**, 1 **0** |
| 3 | Website quality | High / clear offer **15**, Basic **8**, Poor/none **0** |
| 4 | Business maturity | Case studies/testimonials **15**, Limited **8**, None **0** |
| 5 | Revenue indicators | Clear revenue + structured offering **10**, Some **5**, Unclear **0** |
| 6 | Pain / need signals | Hiring/scaling/operational pressure **25**, Some **12**, None **0** |
| 7 | Service clarity | Clear offer **10**, Somewhat clear **5**, Unclear **0** |

For **rows 3–6** (website quality, business maturity, revenue, pain), use the **same evidence definitions and signal counts** as in the Agency table above (company **website** + **LinkedIn company Page** + **job posts** / scaling narrative); only the **point weights** differ (15/8/0, 15/8/0, 10/5/0, 25/12/0). Row **3 (Website quality)** must still be supported by the **Step 3 website-analysis dimensions** (Speed, Mobile, SEO, E-commerce, Aesthetic) in the `Websites reviewed` block, same as Agency.

Geography: prefer contact **country** from HubSpot, then Apollo person country, then org HQ.

---

## Step 6 — Priority bands (both models)

| Score   | Band |
|---------|------|
| 80–100  | **High Priority** |
| 60–79   | **Medium** |
| 40–59   | **Low** |
| \< 40   | **Disqualified** |

If the math yields **\< 40** on a classified Agency/Business Owner lead, treat the **priority band** as Disqualified (you may keep the raw sum in `lead_score_details` for audit).

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
- **`lead_score_details`:** A **multi-line text** field. Put **everything** here: (1) a short run header, (2) **every scoring row** for the model used with **points and explicit reasoning** per criterion (why that tier / points — tie to evidence and the Step 5 rubric), (3) data-source and research audit lines. **Do not omit scoring rows.** Do **not** duplicate this block into `hs_content_membership_notes` unless your portal separately requires that field for another workflow.

**Suggested structure (in order):**

```
--- QUALIFICATION <ISO date> ---
Pathway: Agency | White label OR Business Owner | Direct subscription OR Disqualified
Classification: Agency | Business Owner | Disqualified
Model used: Agency (100) | Business Owner (100) | N/A
Score: <n>/100 | Band: High | Medium | Low | Disqualified

[Scoring — each line: label, points, then reasoning]

Data sources: Apollo OK | Apollo unavailable or partial — Sales Navigator + website
Apollo person summary: <1-3 lines, or "N/A — see LinkedIn/website notes">
Apollo org summary: <1-3 lines, or "N/A — see LinkedIn/website notes">
LinkedIn / Sales Navigator: <activity, positioning, employee hints from profile>
Websites reviewed: <for each URL: 1-line business takeaway + compact Speed | Mobile | SEO | E-commerce | Aesthetic — see Step 3 table>
```

**Agency model — after the header, include all 9 scored rows** (labels match Step 5A). Each line: **`Criterion: <points> — <reasoning>`** (reasoning must justify the tier against the rubric).

```
Lead type (Agency): <n> — <why Agency vs other; if N/A explain>
Geography: <n> — <country/source; why US/AU/UK/CA/Other tier>
Company size: <n> — <band + evidence: Apollo / LinkedIn / unknown>
LinkedIn activity: <n> — <active / semi / inactive + what you saw>
Website quality: <n> — <high/basic/poor + key signals from Step 3>
Business maturity: <n> — <tier + proof signals found or missing>
Revenue indicators: <n> — <tier + commercial structure evidence>
Pain / need signals: <n> — <tier + jobs/scaling evidence or absence>
Service clarity: <n> — <niche / generalist / unclear + why>
```

**Business Owner model — 7 scored rows** (labels match Step 5B), same **`Criterion: <points> — <reasoning>`** pattern (no “Lead type (Agency)” or “LinkedIn activity” rows).

Filled example (Agency — abbreviated reasoning; expand to your actual evidence):

```
--- QUALIFICATION 2026-04-20 ---
Pathway: Agency | White label
Classification: Agency
Model used: Agency (100)
Score: 82/100 | Band: High Priority

Lead type (Agency): 20 — SN + site sell services to clients; white-label ICP.
Geography: 15 — Contact country US (HubSpot); full US tier.
Company size: 10 — Apollo org ~12 FTE; aligns 5–20 band.
LinkedIn activity: 5 — Posts ~biweekly; not weekly → semi-active.
Website quality: 10 — HTTPS, clear services nav, CTA; Step 3 analysis: speed snappy, mobile clean, SEO basics OK, N/A e-com (services), modern UI — met high-tier signal count.
Business maturity: 10 — Named case study + client logos on site and company Page posts.
Revenue indicators: 5 — Clear client work, packages mentioned but no explicit retainer copy.
Pain / need signals: 5 — One open delivery role on LinkedIn Jobs; weak scaling narrative.
Service clarity: 2 — Positioning is broad “digital marketing” vs sharp niche.

Data sources: Apollo OK
Apollo person summary: …
Apollo org summary: …
LinkedIn / Sales Navigator: …
Websites reviewed: https://example.com — clear offer; Speed: snappy | Mobile: nav OK narrow | SEO: title+H1 sensible | E-commerce: N/A service site | Aesthetic: polished contemporary.
```

For **Disqualified**, lead with **`Disqualified: <reason>`** on the first content line, set **`lead_score`** to **`0`**, and use **`N/A — <brief why>`** on rubric lines only when you did not apply the numeric model; otherwise still briefly justify any partial assessment you did make.

**`hs_lead_status` rules (align with outreach):**

- If **Disqualified** (explicit DQ or band \< 40): set to **`UNQUALIFIED`** if that value exists in your portal; otherwise keep `NEW` and make the band explicit in **`lead_score_details`**.
- If **qualified** (band Low or better, score ≥ 40): set to **`IN_PROGRESS`** so [lead-outreach.md](./lead-outreach.md) can pick them up for LinkedIn messaging.

**Business Owner:** use the same **`lead_score_details`** structure: the **7 scored rows** from Step 5B (Geography through Service clarity), each with points and reasoning — no “Lead type (Agency)” or “LinkedIn activity” rows.

If your HubSpot has **custom contact properties** (e.g. `sales_pathway`, `priority_band`), fill them in addition to **`lead_score`** and **`lead_score_details`** for reporting.

---

## Step 8 — Report

Output a table:

| Name | Company | Classification | Pathway | Score (`lead_score`) | Band | HubSpot updated |
|------|---------|----------------|---------|----------------------|------|------------------|

If PATCH fails, record the error and continue with the next contact.

---

## Step 9 — Send Slack alert for high-intent qualified leads

After reporting, send a Slack notification for each lead where **`lead_score` is greater than 70**.

**Trigger condition:**

- Lead qualified with **`lead_score` > 70** (**High intent detected**).

Use this command format:

```bash
openclaw message send --channel slack --target "channel:C0B0GAZ032L" --message "MESSAGE"
```

**Message requirements (include all fields):**

- Header line: `MOSTLY — Lead Qualified - <lead_score> Score`
- Name
- Company
- Conversation summary
- LinkedIn profile link

**Recommended message template:**

```text
MOSTLY — Lead Qualified <lead_score>
Name: <firstname lastname>
Company: <company>
Conversation summary: <short 1-3 sentence summary from lead_score_details / qualification notes>
LinkedIn profile link: <hs_linkedin_url>
```

If Slack send fails, log the failure in the run output and continue with the next lead.
