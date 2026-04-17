# Project Inception: Title Efficiency Quotient (TEQ)

**Date:** 2026-04-16  
**PI:** Seth C. Oranburg, UNH Franklin Pierce School of Law  
**Project:** TEQ — Title Efficiency Quotient

## Research Question

Do measurable features of law review article titles predict citation impact and/or placement tier?

## Null Hypothesis

Title features have no statistically significant relationship to article impact after controlling for author prestige, journal rank, and subject matter.

## Data Sources

- **W&L Law Journal Rankings**: 1,565 journals across multiple categories. Five CSV files covering Combined, Impact, Currency, and category-specific rankings. This is our source of truth for journal-level quality metrics.
- **Article-level data**: TBD. Candidates include HeinOnline, SSRN, Google Scholar, Crossref. Collection methodology to be determined in Phase 1.

## Initial Candidate Features

1. Word count
2. Character count
3. Has colon (subtitle indicator)
4. Has question mark
5. Has subtitle (colon or em-dash)
6. Title case ratio
7. Flesch reading ease
8. Average word length
9. Jargon density (legal terms per word)
10. Novelty score (inverse frequency of title bigrams in corpus)
11. Abstractness score (ratio of abstract to concrete nouns)
12. Named entity count
13. Sentiment polarity
14. Punctuation density
15. Use of quotation marks
16. Contains numeric reference (e.g., year, statute number)
17. Contains proper noun (case name, jurisdiction)
18. Alliteration score
19. Title length relative to journal median
20. Keyword overlap with journal stated scope

## Statistical Approach

- **Primary method:** OLS regression with dependent variable = citation count (log-transformed) or placement tier.
- **Controls:** Author prestige (h-index or institution rank), journal rank (W&L combined score), subject matter (fixed effects by category).
- **Validation:** k-fold cross-validation (k=5 or 10).
- **Multiple comparisons:** Bonferroni correction or FDR control.
- **Robustness:** Alternative specifications, subsample analysis, sensitivity to outliers.

## Notes

This project was initiated after observing informal patterns in title characteristics across high- and low-placement law review articles. The goal is to move from anecdote to evidence. If no features predict impact, that is itself a publishable finding.
