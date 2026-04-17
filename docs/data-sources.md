# TEQ Data Sources Assessment

Assessed 2026-04-16 during project setup. This document records what we learned about each potential data source, what works, what doesn't, and what each source provides.

## Source of Truth: W&L Law Journal Rankings

**File:** `data/sources/2024-LawJ-Master.csv` (read-only, chmod 444)
**Records:** 400 ranked English-language law journals
**Fields:** rank, name, combined score, impact factor, journals cited, currency score, cases cited, scope (General/Specialized), editing (Student-Edited/Peer-Edited/Refereed), format (Print/Online)
**How acquired:** Exported from W&L Law Journal Rankings interface (https://managementtools4.wlu.edu/LawJournals/). Five filtered exports were merged programmatically to add scope, editing, and format metadata.
**Status:** Loaded into database. Validated against cross-exports. Clean.

## Crossref API

**URL:** https://api.crossref.org/works
**Cost:** Free, no API key required. Polite pool available with mailto parameter.
**What it provides:** Article titles, authors, DOIs, year, volume, citation counts (is-referenced-by-count).
**What works:** Peer-reviewed and refereed journals (e.g., American Journal of International Law, Journal of Legal Analysis, Journal of Law and Economics). ISSN-based queries return precise results.
**What does NOT work:** Student-edited law reviews do not deposit metadata with Crossref. Columbia, Harvard, Yale, Stanford, and all T14 flagships return zero results. This eliminates Crossref as a source for the most important journals in the study.
**Script:** `scripts/collect_crossref.py`
**Recommendation:** Use for the ~68 peer-reviewed/refereed journals in our dataset. Not viable for student-edited journals.

## Journal Websites (Direct Scraping)

**What it provides:** Article titles, authors, volume/issue, topic tags (some sites), abstracts (some sites).
**What it does NOT provide:** Citation counts, piece type labels (article vs. note vs. essay), author affiliation.
**What works:** 25 journal sites are currently accessible and scrapable. Fordham, Iowa, Yale, Harvard, Duke, NYU, Minnesota, Northwestern, Texas, UCLA, and others. 1,466 articles collected in initial scrape.
**What does NOT work:** Columbia, Stanford, Cal, Cornell, Michigan, Virginia, Georgetown, and ~28 others return 403 (Cloudflare bot protection). These sites are browsable in a real browser but block automated requests.
**Workaround for blocked sites:** User saves HTML pages via Cmd+S, then `scripts/parse_journal_html.py` parses the saved files. Tested on 3 Columbia Law Review issues (14 articles extracted).
**Scripts:** `scripts/collect_journal_sites.py` (automated), `scripts/parse_journal_html.py` (manual HTML), `scripts/discover_journal_sites.py` (site discovery)
**Recommendation:** Good for titles and authors at scale. Combine with other sources for citation counts and piece type.

## HeinOnline

**URL:** https://heinonline.org (institutional access required)
**What it provides:** Article titles, authors, page counts, ScholarCheck citation counts, full text PDFs, section type labels (Article/Note/Comment/Book Review in scanned TOCs).
**What we learned:** 
- ISSN search in the "Search the Catalog" section finds the publication, not individual articles.
- The Law Journal Library search has fields for Text, Article Title, Author/Creator, Description, State, Country, Date, DOI. No "Publication Title" dropdown.
- Browsing to a specific journal and volume shows a scanned TOC image with section labels (ARTICLE, NOTES, BOOK REVIEW) but this is not structured/exportable data.
- ScholarCheck was not found in the interface during testing. May require a different subscription level or navigation path.
- No bulk CSV export path was identified during this session.
**Script:** `scripts/process_heinonline.py` (ready for CSV imports if export path is found)
**Recommendation:** Richest source for legal scholarship but export workflow needs further investigation. Key value: piece type labels and citation counts. Consider contacting HeinOnline support about bulk export or ScholarCheck API access.

## Westlaw

**URL:** https://www.westlaw.com (institutional access required)
**What it provides:** Article titles, authors, piece types, citation counts, KeyCite data.
**What we learned:** Westlaw is a single-page application. Saving the page as HTML (Cmd+S) captures only the empty shell; article content loads dynamically via JavaScript and is not present in the saved HTML. The Columbia Law Review page showed "Coverage begins with 1951" and promised "10 most recent" documents, but the article list was not in the saved file.
**Script:** None built. SPA architecture prevents simple scraping or HTML parsing.
**Recommendation:** Not viable for automated collection. Could potentially be accessed via Westlaw Edge API (if available through institutional license) or browser automation (Playwright). Low priority given other options.

## Google Scholar (via scholarly library)

**URL:** https://scholar.google.com (no official API)
**What it provides:** Citation counts (broadest coverage), author profiles (h-index, i10-index, affiliation, interests).
**What we learned:** The `scholarly` Python library works but is slow (3-8 second delays between requests to avoid blocking) and fragile. Useful for author profile lookups and citation validation on small samples.
**Script:** `scripts/collect_scholar.py`
**Recommendation:** Use for author profile enrichment (h-index, affiliation) and as a validation source for citation counts on random subsamples. Not viable as a primary citation source at scale due to rate limiting.

## SerpAPI (Google Scholar API)

**URL:** https://serpapi.com/google-scholar-api
**What it provides:** Structured JSON access to Google Scholar search results. Citation counts, author profiles, article metadata. Supports `source:` parameter for journal-specific searches and date filtering.
**Pricing:**
- Free: 250 searches/month (enough to validate pipeline)
- Developer: $75/month for 5,000 searches (enough for full dataset)
- Production: $150/month for 15,000 searches
**Estimated cost for project:** ~10,000 article title searches = 2 months at Developer tier = $150 total.
**Script:** Not yet built. Requires API key (sign up at serpapi.com).
**Recommendation:** Best option for citation counts at scale. Clean API, structured JSON, no scraping fragility. Sign up for free tier to validate, then upgrade to Developer for full collection. Build collector as next priority.

## ORCID

**URL:** https://pub.orcid.org/v3.0/ (free public API, no authentication required)
**What it provides:** Author disambiguation, ORCID IDs, current and historical affiliations, employment history, publication lists.
**Script:** `scripts/collect_orcid.py`
**Recommendation:** Best source for author affiliation data, which is the key control variable for prestige independence. Use to enrich Author records with affiliation_at_publication.

## Sources NOT Pursued

**SSRN:** No API. Download counts are available but require web scraping. Match rate with law review articles is uneven (higher for T14/well-known authors, lower for others). Missingness correlates with prestige, creating a selection bias problem. Low priority.

**ResearchGate:** No API, aggressive anti-scraping. Duplicate coverage with Google Scholar and ORCID. Not worth the effort.

## Data Collection Priority Order

1. **SerpAPI** (sign up, build collector, get citation counts for all articles)
2. **ORCID** (enrich author records with affiliations)
3. **Journal websites** (expand scraper to more sites, continue collecting titles)
4. **HeinOnline** (investigate export/ScholarCheck access for piece type labels)
5. **Crossref** (collect peer-reviewed journal articles)
6. **Google Scholar via scholarly** (author profiles, validation samples)

## Classification Problem: Piece Types

Journal websites and Crossref do not label pieces as article, note, essay, book review, symposium contribution, etc. HeinOnline scanned TOCs have these labels but in image form (not structured data). Westlaw has them but is not exportable.

Options for classification:
1. Manual coding by RA (gold standard, expensive: ~500 articles at 2 min each = 17 hours)
2. Heuristic classifier using title patterns and author signals (built in parse_journal_html.py, accuracy unknown)
3. Train a classifier on a manually-coded sample, apply to the rest
4. Use HeinOnline section labels if bulk export becomes available

Current status: piece_type field exists on Article model but is not populated. All scraped articles have piece_type=unknown or heuristic guesses that need validation.

## Classification Problem: Author Types

Similarly, we cannot reliably distinguish faculty from students from practitioners from judges using only the data available from journal websites. The author footnote (e.g., "Professor of Law at..." vs. "J.D. Candidate...") contains this information but requires full-text access.

Options:
1. ORCID enrichment (gives affiliation, which distinguishes faculty from others)
2. Manual coding
3. Pattern matching on asterisk conventions (unreliable)
