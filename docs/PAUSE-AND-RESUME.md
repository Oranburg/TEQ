# TEQ Project: Pause and Resume

Last updated: April 17, 2026

This project is paused while the PI focuses on book manuscripts. This document captures everything needed to resume work without losing context.

## Current State

**Repo:** `/Users/sco/teq/` and `github.com/Oranburg/TEQ`

**Data collected:**

- 400 journals loaded from W&L master CSV (read-only in `data/sources/`)
- ~1,480 articles scraped from 25 journal website configurations
- HTML parser for saved journal pages (tested on 3 Columbia issues)

**Database:** SQLite at `data/teq.db` with these models:

- Journal, Article, Author, TitleFeature, Hypothesis, ExperimentRun, AuditLog
- Author model uses many-to-many join table with `affiliation_at_publication` field

**Collector scripts built (5):**

1. Crossref -- works for peer-reviewed journals only
2. HeinOnline CSV processor
3. Google Scholar (scholarly library)
4. ORCID
5. Journal website scraper (25 sites configured)

**Tests:** All 24 passing.

## What Was NOT Done Yet

- **SerpAPI collector not built.** Need API key signup at serpapi.com; $75/mo developer tier for 5,000 searches.
- **No article-level citation counts collected yet.** This is the main gap.
- **Feature extraction pipeline:** 6 features implemented, 8 stubs remaining, and the research design calls for 40 total.
- **No hypotheses registered yet.**
- **No statistical analysis begun.**
- **HeinOnline bulk export path not found;** Westlaw is a SPA and cannot be scraped.
- **Piece-type classification** (article vs. note vs. essay) remains unsolved.

## To Resume, Do These Things in Order

1. Sign up for SerpAPI free tier and get an API key.
2. Build the SerpAPI collector script (model after `collect_crossref.py`).
3. Run the Crossref collector on peer-reviewed journals:
   ```
   PYTHONPATH=src python3 scripts/collect_crossref.py --tier 4
   ```
4. Run the SerpAPI collector on existing articles to get citation counts.
5. Implement remaining feature extraction stubs (see `docs/TEQ-research-design.md` Section 4 for all 40 features).
6. Register the 10 starter hypotheses from the research design.
7. Begin exploratory analysis in `notebooks/`.

## Key Documents

| File | Purpose |
|------|---------|
| `docs/data-sources.md` | Comprehensive assessment of all data sources |
| `docs/TEQ-research-design.md` | Full research methodology |
| `docs/TEQ-Copilot-Prompt.md` | The original scaffolding prompt |
| `docs/gemini-framework.md` | Gemini's framework (NOT source of truth, reference only) |
| `CLAUDE.md` | Repo rules and conventions |

## Key Principle

The formula is the OUTPUT of the research, not the input. Do not build a scoring formula until Phase 5.
