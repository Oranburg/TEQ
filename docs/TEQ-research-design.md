# TEQ Project: Research Design

Seth C. Oranburg, UNH Franklin Pierce School of Law

April 2026


## 1. Research Question and Core Premise

The TEQ project asks: **do measurable features of law review article titles predict academic impact, and if so, which features matter most?**

The formula is the output, not the input. Prior iterations of this project (TEQ 1.0, 2.2) made a category error: they specified a formula first and then ran data through it to "validate" the formula. That is circular. The correct approach is to extract dozens of candidate title features, measure their individual and joint predictive power against observed impact outcomes, and let the data reveal which features belong in any eventual model---and with what weights.

The study belongs to a growing empirical literature on academic knowledge production. Relevant predecessors include Christensen & Eining (1991) on accounting journal title characteristics, Jamali & Nikzad (2011) on the effect of title type on citation counts, and Letchford et al. (2015) on the relationship between short titles and high citations in nature journals. The legal academy has no comparable study. Given that law reviews are student-edited (introducing a distinctive gatekeeper dynamic), findings from other disciplines cannot simply be imported.


## 2. Data Architecture

The study requires three linked datasets.

### 2.1 Baseline Dataset: Journal-Level (Already Acquired)

Source: Washington & Lee Law Journal Rankings (2024), all 1,565 journals.

Fields available: Rank, Journal Name, Combined Score (20-24), Impact Factor (20-24), Journals Cited (20-24), Currency (20-24), Cases Cited (20-24).

This dataset serves as the control for journal prestige. Every article in the study will be linked to its journal's W&L rank and impact factor.

Additional journal-level variables to construct:

- **Journal type**: general vs. specialty, flagship vs. secondary, peer-reviewed vs. student-edited. The W&L subcategory files (General/Student/Print, Specialized/Peer/Print, Specialized/Student/Print, Online) provide this taxonomy directly.
- **School rank**: the U.S. News ranking of the law school that publishes the journal. This is the second layer of prestige control. Source: public U.S. News data, hand-coded to the 1,565 journals.

### 2.2 Article-Level Dataset (To Be Constructed)

This is the core dataset. Each row is one article. Required fields:

| Field | Source | Collection Method |
|---|---|---|
| Article title | Crossref, HeinOnline | API (Crossref); scrape or bulk export (Hein) |
| Author(s) | Crossref, HeinOnline | Same |
| Journal name | Crossref, HeinOnline | Same; linked to W&L baseline |
| Volume / year | Crossref, HeinOnline | Same |
| Publication type | Derived from title + metadata | Algorithmic + manual audit |
| Page count | HeinOnline | Bulk export |
| Crossref citation count | Crossref API | API (`is-referenced-by-count`) |
| Google Scholar citation count | Google Scholar | Scrape (with caution; see below) |
| SSRN download count | SSRN | API or scrape (see below) |
| HeinOnline ScholarCheck metrics | HeinOnline | Manual or institutional access |

**Sampling strategy.** The unit of observation is a faculty-authored flagship article (not student notes, book reviews, tributes, or symposium introductions). The categorization schema from the Gemini prototype (Codes 0-5) is a reasonable starting taxonomy, but assignment must be validated by human audit on a random 10% sample.

**Sample size and power.** For a multiple regression with approximately 30 candidate predictors, detecting a small-to-medium effect size (f-squared = 0.05) at alpha = 0.05 and power = 0.80 requires roughly 700 observations. But we are not running a single regression. We need enough data for training/test splits, subgroup analyses (general vs. specialty journals, T14 vs. non-T14), and cross-validation. Target: **5,000 articles minimum, 10,000 preferred.**

To reach 10,000 articles, scrape complete volumes from a stratified sample of journals:

- **Tier 1 (T14 flagships):** All 14 main law reviews, 3 recent volumes each. Approximately 40 articles per volume = ~1,680 articles.
- **Tier 2 (Ranked 15-50, general):** 20 journals, 3 volumes each = ~2,400.
- **Tier 3 (Ranked 51-150, general):** 20 journals, 2 volumes each = ~1,600.
- **Tier 4 (Specialty journals, top 30 by W&L specialty ranking):** 30 journals, 2 volumes each = ~2,400.
- **Tier 5 (Ranked 150+, general):** 15 journals, 2 volumes each = ~1,200.

This gives roughly 9,280 raw articles before filtering out non-flagship pieces. After filtering, expect approximately 5,500-6,500 flagship articles. The unfiltered dataset is preserved for robustness checks comparing flagship-only and all-articles models.

**Time window.** Volumes published 2018-2023, providing a 3-8 year citation window. Articles published before 2018 have longer citation windows but predate current titling trends (e.g., "in the Age of X" constructions increased sharply after 2016). Articles published after 2023 have insufficient citation accumulation.

### 2.3 Author-Level Dataset (To Be Constructed)

This dataset addresses the "Prestige Independence" problem (Section 7). Each unique author receives a row with prestige proxies:

| Field | Source | Method |
|---|---|---|
| Author name | Article dataset | Inherited |
| Institutional affiliation at time of publication | HeinOnline, SSRN profiles, article itself | Semi-manual |
| School U.S. News rank | U.S. News | Lookup |
| Career citation count (h-index proxy) | Google Scholar profile | Scrape or manual |
| Prior publications in T14 journals | Article dataset + HeinOnline | Computed |
| Years since first publication | HeinOnline | Computed |


## 3. Data Collection: Source-by-Source Assessment

### 3.1 Crossref API

**What it provides:** Title, authors, volume, year, DOI, citation count (`is-referenced-by-count`), abstract (sometimes), references (sometimes). Well-structured JSON.

**Access:** Free, public REST API. Polite pool requires `mailto` parameter. Rate limit: ~50 requests/second with polite headers.

**Coverage:** Good for post-2010 law reviews. Many law reviews register DOIs via Crossref. Coverage is incomplete for older volumes and some specialty journals.

**Collection script architecture:**
1. For each target journal, look up the ISSN in the W&L baseline.
2. Query `https://api.crossref.org/journals/{ISSN}/works?filter=from-pub-date:2018,until-pub-date:2023&rows=100&offset=0`.
3. Paginate through all results.
4. Store raw JSON; parse into flat CSV.

**Limitation:** Citation counts are typically lower than Google Scholar counts because Crossref only counts citations from works that themselves have DOIs and are registered with Crossref. Useful as one measure but not the sole dependent variable.

### 3.2 HeinOnline

**What it provides:** Full article metadata, page counts, ScholarCheck citation counts, author information, PDF full text. The most complete source for legal scholarship.

**Access:** Institutional subscription required. No public API. HeinOnline does offer a "bulk data" service for institutional partners and researchers. Alternatively, data can be exported via the "ScholarCheck" and "Law Journal Library" search interfaces, which allow downloading CSV result sets of up to 10,000 records per query.

**Strategy:** Use HeinOnline's advanced search to pull all articles from each target journal/volume. Export metadata as CSV. ScholarCheck provides citation counts from within the HeinOnline corpus. This is the most reliable citation measure for legal scholarship because it captures law review citations that Google Scholar and Crossref often miss.

**Limitation:** Manual effort per journal unless institutional bulk access is negotiated. Budget 30 minutes per journal for search, filter, and export. For 99 journals, that is approximately 50 hours of RA time.

### 3.3 SSRN

**What it provides:** Download counts, abstract views, author profiles. Download count is a distinct measure of "market" impact---it captures reader interest before (and independent of) citation.

**Access:** SSRN has no public API. The SSRN website can be searched by author or title. Download counts are displayed on individual paper pages.

**Strategy:** For each article in the dataset, search SSRN by title. If a match is found, record the download count. This must be automated with a web scraper (e.g., Python + Selenium or Playwright) or semi-automated with manual spot-checking.

**Limitation:** Not all law review articles are posted on SSRN. Match rate will be highest for T14 and well-known authors (perhaps 60-70%) and lower for Tier 5 journals. Missingness is non-random---it correlates with author prestige---and must be modeled accordingly (see Section 6.3).

### 3.4 Google Scholar

**What it provides:** Citation counts (broadest coverage, including books, working papers, foreign-language sources).

**Access:** No official API. Google actively blocks automated scraping. The `scholarly` Python library exists but is fragile and rate-limited.

**Strategy:** Use Google Scholar as a validation/robustness check rather than a primary source. Pull GS citation counts for a random 500-article subsample and compare to Crossref and HeinOnline counts. If the rank-order correlation exceeds 0.85, the primary Crossref/HeinOnline measures are sufficient.

**Alternative:** Semantic Scholar API (free, documented, stable) indexes some legal scholarship. Test coverage on a 100-article pilot before committing.


## 4. Feature Extraction Pipeline

Every article title is processed to extract the following candidate predictors. Features are organized by category. All features are computed algorithmically; manual coding is used only for validation.

### 4.1 Length Features

| Feature | Definition | Rationale |
|---|---|---|
| `char_count` | Total characters including spaces | Raw length |
| `word_count` | Total words (whitespace-delimited) | Readable length |
| `log_char_count` | ln(char_count) | Diminishing returns hypothesis |

### 4.2 Punctuation and Structure

| Feature | Definition | Rationale |
|---|---|---|
| `has_colon` | Binary: title contains colon | Subtitle presence; two-part structure |
| `has_question_mark` | Binary: title ends in ? | Interrogative framing |
| `has_em_dash` | Binary: title contains em/en dash | Parenthetical or appositional structure |
| `has_comma` | Binary: title contains comma | List or embedded clause |
| `num_punctuation` | Count of all punctuation marks | Overall punctuation density |
| `subtitle_length_ratio` | If colon present: words after colon / total words | Balance of main title vs. subtitle |

### 4.3 Structural Templates

Binary flags for common law review title patterns. Detected via regex.

| Feature | Pattern | Example |
|---|---|---|
| `tmpl_the_x_of_y` | ^The \w+ of | "The Limits of Contract" |
| `tmpl_beyond_x` | ^Beyond | "Beyond Efficiency" |
| `tmpl_rethinking_x` | ^(Rethinking\|Reconsidering\|Reimagining\|Reexamining) | "Rethinking Standing" |
| `tmpl_x_in_age_of_y` | in the (Age\|Era\|Time\|Wake) of | "Privacy in the Age of AI" |
| `tmpl_toward_x` | ^Toward[s]? | "Toward a Theory of..." |
| `tmpl_x_and_y` | ^\w+ and \w+$ (exactly two nouns) | "Property and Personhood" |
| `tmpl_against_x` | ^Against | "Against Settlement" |
| `tmpl_defense_of_x` | (In Defense of\|Defending) | "In Defense of Judicial Engagement" |
| `tmpl_death_of_x` | (Death of\|End of\|Demise of) | "The Death of the Irreparable Injury Rule" |

### 4.4 Doctrinal and Legal Signals

| Feature | Definition | Detection Method |
|---|---|---|
| `has_case_name` | Binary: title contains a v. or vs. construction | Regex: `\b\w+ v\.? \w+` |
| `has_statute_ref` | Binary: title references a statute or section number | Regex: `\b(Section\|Act\|\u00a7)\b` or USC pattern |
| `has_amendment_ref` | Binary: title references a constitutional amendment | Regex: `(First\|Second\|...\|Fourteenth) Amendment` |
| `has_jurisdiction` | Binary: title names a specific jurisdiction | NER (GPE entities) or dictionary lookup |
| `num_legal_terms` | Count of terms from a legal vocabulary list | Dictionary of ~500 legal terms of art |
| `legal_term_density` | num_legal_terms / word_count | Normalized doctrinal density |

### 4.5 Novelty and Creativity

| Feature | Definition | Detection Method |
|---|---|---|
| `has_neologism` | Binary: title contains a word not in standard dictionary | Dictionary comparison (aspell or nltk wordlist) |
| `has_pop_culture` | Binary: title references pop culture | Dictionary of common pop culture terms/names |
| `has_metaphor_signal` | Binary: title uses metaphorical language markers | Presence of "as," figurative verbs (e.g., "weaponize," "unlock") |
| `title_novelty_score` | TF-IDF uniqueness relative to all other titles in corpus | Computed post-collection: cosine distance from corpus centroid |
| `has_alliteration` | Binary: two or more consecutive words share first letter | Regex on first characters |

### 4.6 Sentiment and Tone

| Feature | Definition | Detection Method |
|---|---|---|
| `sentiment_polarity` | Continuous [-1, 1]: negative to positive | VADER or TextBlob sentiment |
| `sentiment_subjectivity` | Continuous [0, 1]: objective to subjective | TextBlob subjectivity |
| `is_provocative` | Binary: title uses strong/charged language | Custom dictionary (e.g., "myth," "lie," "failure," "broken") |
| `has_normative_verb` | Binary: title contains "should," "must," "ought" | Regex |

### 4.7 NLP Features

| Feature | Definition | Detection Method |
|---|---|---|
| `noun_ratio` | Proportion of words that are nouns | spaCy POS tagging |
| `adj_ratio` | Proportion of words that are adjectives | spaCy POS tagging |
| `verb_ratio` | Proportion of words that are verbs | spaCy POS tagging |
| `named_entity_count` | Number of named entities (people, orgs, places) | spaCy NER |
| `named_entity_density` | named_entity_count / word_count | Normalized |
| `semantic_similarity_to_journal` | Cosine similarity between title embedding and journal's typical title embedding | Sentence-BERT embeddings |
| `abstractness_score` | Average word concreteness rating | Brysbaert et al. (2014) concreteness norms |

### 4.8 Computed Interaction Features (Generated After Initial Analysis)

These are not extracted directly but derived from combinations of the above:

- `length_x_colon`: interaction between word count and colon presence
- `novelty_x_specialty`: interaction between novelty score and journal specialty status
- `legal_density_x_rank`: interaction between legal term density and journal W&L rank

Interaction features are tested only if main effects are significant, to limit the multiple comparisons problem.

**Total initial candidate features: approximately 40.**


## 5. Statistical Analysis Plan

### 5.1 Dependent Variables

Three dependent variables, each capturing a different dimension of impact:

| DV | Source | Transformation |
|---|---|---|
| `cite_crossref` | Crossref `is-referenced-by-count` | ln(1 + count) to address right skew |
| `cite_hein` | HeinOnline ScholarCheck | ln(1 + count) |
| `downloads_ssrn` | SSRN download count | ln(1 + count) |

Each model is run separately on each DV. Concordance across DVs strengthens findings; divergence reveals that different title features predict different kinds of impact (itself an interesting result).

### 5.2 Control Variables

These variables must be included in every regression to isolate the title effect from confounders:

| Control | Operationalization | Source |
|---|---|---|
| `journal_wl_rank` | W&L Combined Score (continuous) | Baseline dataset |
| `journal_type` | Factor: general, specialty, online | W&L subcategory files |
| `school_usnews_rank` | U.S. News ranking of publishing school | Public data |
| `author_prestige` | See Section 7 | Constructed |
| `pub_year` | Publication year (factor or continuous) | Article dataset |
| `article_pages` | Page count (proxy for article length) | HeinOnline |
| `subject_area` | Topic classification (see below) | LDA or manual coding |

**Subject area classification.** Articles are classified into approximately 15-20 subject areas using Latent Dirichlet Allocation (LDA) on article abstracts (where available) or full text (where accessible via HeinOnline). For articles without abstracts, the journal's specialty designation plus title keywords serve as a fallback. Subject area enters the regression as a fixed effect, absorbing variation due to field-specific citation norms (constitutional law articles are cited differently than tax articles).

### 5.3 Analysis Sequence

The analysis proceeds in four stages. Each stage is pre-registered (Section 6) before execution.

**Stage 1: Descriptive Statistics and Univariate Screening.**

For each of the ~40 candidate features, compute:
- Mean, median, standard deviation, min, max
- Pearson and Spearman correlation with each DV
- Visualizations: histograms of feature distributions, scatterplots of feature vs. DV

Apply Bonferroni correction for multiple comparisons (alpha = 0.05/40 = 0.00125). Features that are not significant at the corrected level in univariate screening are flagged but not automatically excluded from multivariate analysis (because suppressor effects exist).

**Stage 2: Multivariate Regression.**

Ordinary Least Squares regression with robust (heteroskedasticity-consistent) standard errors:

```
ln(1 + citations) = beta_0 + beta_1(controls) + beta_2(title features) + epsilon
```

Run in a hierarchical / nested sequence:

- **Model A (controls only):** All control variables, no title features. This establishes the baseline R-squared---how much variation is explained by journal rank, author prestige, year, and subject matter alone.
- **Model B (controls + length):** Add length features only.
- **Model C (controls + structure):** Add punctuation and template features.
- **Model D (controls + content):** Add doctrinal signals, novelty, sentiment.
- **Model E (controls + NLP):** Add NLP-derived features.
- **Model F (full model):** All features.

Compare R-squared increments (delta-R-squared) between models. The increment from Model A to Model F is the total "title effect"---the variance in citations explained by title features after controlling for prestige, journal, year, and topic. Report F-tests for each block of added features.

**Stage 3: Regularized Regression and Feature Selection.**

Because 40+ features risk overfitting, use LASSO (L1 regularization) and Elastic Net to perform automated feature selection:

- LASSO shrinks weak predictors' coefficients to exactly zero, producing a parsimonious model.
- Elastic Net combines L1 and L2 penalties, handling correlated features better than LASSO alone.
- Tune the regularization parameter (lambda) via 10-fold cross-validation on the training set.
- Report which features survive regularization at lambda_min and lambda_1se.

The surviving features are the empirically validated components of any eventual TEQ formula.

**Stage 4: Nonlinear and Machine Learning Models.**

To check whether the linear regression misses important nonlinearities:

- **Random Forest regression.** Compute feature importance scores (mean decrease in impurity and permutation importance). Compare the importance ranking to the OLS beta ranking.
- **Gradient Boosted Trees (XGBoost).** Same purpose, different algorithm. If tree-based models substantially outperform OLS (measured by cross-validated RMSE), the relationship between title features and impact is nonlinear and a linear TEQ formula would be a poor summary.
- **Partial Dependence Plots.** For the top 5 features by importance, plot the marginal effect of each feature on predicted citations, holding all other features at their mean. This reveals whether the effect is linear, U-shaped, or threshold-based.

### 5.4 Supplementary Analyses

- **Quantile regression.** Does the title effect differ at the 25th, 50th, 75th, and 90th percentiles of citations? A feature that predicts high-citation outliers but not median articles is interesting and practically important.
- **Negative binomial regression.** As a robustness check on the log-transformed OLS, run the models with raw citation counts as the DV using negative binomial regression (appropriate for overdispersed count data).
- **Subgroup analyses.** Run the full model separately for: (a) T14 journals vs. non-T14; (b) general vs. specialty journals; (c) pre-2020 vs. post-2020 (pandemic shift in readership patterns).


## 6. Hypothesis Pre-Registration System

To prevent p-hacking and post-hoc rationalization, every hypothesis is registered before the data are analyzed. The registry is a structured JSON file stored in the project repository.

### 6.1 Hypothesis Entry Schema

```json
{
  "id": "H-001",
  "date_registered": "2026-04-16",
  "status": "registered",
  "stage": "Stage 1",
  "hypothesis": "Shorter titles (lower word_count) are associated with higher citation counts.",
  "direction": "negative",
  "feature": "word_count",
  "dv": "cite_crossref",
  "controls": ["journal_wl_rank", "author_prestige", "pub_year", "article_pages", "subject_area"],
  "test": "Pearson correlation (Stage 1); OLS coefficient (Stage 2)",
  "significance_threshold": 0.00125,
  "rationale": "Letchford et al. (2015) found shorter titles correlate with higher citations in Nature journals. Hypothesis tests whether this generalizes to legal scholarship.",
  "result": null,
  "result_date": null,
  "notes": null
}
```

### 6.2 Status Lifecycle

1. **registered** -- hypothesis written before any data analysis
2. **tested** -- analysis complete, result recorded
3. **supported** -- result matches predicted direction at the pre-specified significance level
4. **not_supported** -- result does not reach significance or goes in the opposite direction
5. **revised** -- hypothesis was modified after initial testing (flagged as exploratory, not confirmatory)

### 6.3 Exploratory vs. Confirmatory

Any hypothesis added after data analysis begins is tagged `"exploratory": true`. Exploratory findings are reported separately and require replication on the held-out test set to be treated as confirmed.

### 6.4 Starter Hypotheses

The following hypotheses are registered as of the project's inception. Each is grounded in prior literature or a theoretical claim about how law review titles function.

| ID | Hypothesis | Direction | Feature | Rationale |
|---|---|---|---|---|
| H-001 | Shorter titles predict higher citations | negative | `word_count` | Letchford et al. (2015) |
| H-002 | Colon presence (subtitle) predicts higher citations | positive | `has_colon` | Subtitles signal specificity |
| H-003 | Question-mark titles predict lower citations | negative | `has_question_mark` | Betteridge's law; questions signal uncertainty |
| H-004 | Case names in titles predict higher citations | positive | `has_case_name` | Doctrinal utility signal |
| H-005 | Higher legal term density predicts higher citations in specialty journals but not general journals | interaction | `legal_term_density * journal_type` | Audience-matching hypothesis |
| H-006 | Neologisms predict higher SSRN downloads but not higher citations | positive (downloads), null (citations) | `has_neologism` | Novelty attracts attention but not doctrinal reliance |
| H-007 | "Rethinking X" template predicts lower citations than "The X of Y" template | negative comparison | `tmpl_rethinking_x` vs. `tmpl_the_x_of_y` | "Rethinking" signals incremental critique; "The X of Y" signals foundational treatment |
| H-008 | Provocative sentiment predicts higher downloads but lower citations | positive (downloads), negative (citations) | `is_provocative` | Provocation attracts clicks but may reduce perceived reliability |
| H-009 | Title novelty (TF-IDF uniqueness) has a curvilinear (inverted-U) relationship with citations | quadratic | `title_novelty_score` | Moderate novelty is optimal; too unique is inaccessible |
| H-010 | The title effect (incremental R-squared) is larger for lower-ranked journals than for T14 journals | subgroup difference | Full model delta-R-squared | At T14 journals, author and journal prestige dominate; at lower-ranked journals, title quality may matter more |


## 7. The Prestige Independence Problem

This is the hardest methodological challenge. Author prestige, journal prestige, article quality, and title quality are all correlated. A Harvard professor publishes in the Harvard Law Review with a straightforward title and gets 200 citations. Is that because of the title, the author, the journal, or the article? Disentangling these requires more than throwing control variables into a regression.

### 7.1 Strategy 1: Hierarchical Controls (Minimum Viable)

Include both journal-level and author-level prestige measures as control variables. The title features' coefficients represent the title effect conditional on prestige. This is the standard approach and the weakest. It assumes the functional form of the prestige effect is correctly specified (likely linear in rank, but maybe not).

### 7.2 Strategy 2: Journal Fixed Effects

Replace the continuous journal rank variable with journal-level fixed effects (dummy variables for each journal). This absorbs all between-journal variation, including journal prestige, editorial preferences, and audience size. The title effect is estimated entirely from within-journal variation---comparing articles published in the same journal to each other.

Trade-off: with 99 journals and fixed effects, we lose 98 degrees of freedom. With 5,000+ observations, this is affordable. The within-journal estimator is the cleanest test of whether title features predict citation variation among articles published in the same venue.

### 7.3 Strategy 3: Author Fixed Effects (Where Feasible)

For prolific authors who appear multiple times in the dataset, include author-level fixed effects. This compares different articles by the same author, holding constant everything about the author (reputation, network, writing quality, field). The title effect is estimated from variation across an individual author's publications.

Limitation: most authors appear only once or twice in any 5-year window. Author fixed effects are feasible only for a subset of highly prolific scholars. This analysis is a robustness check, not the main specification.

### 7.4 Strategy 4: Propensity Score Matching

Construct a "prestige propensity score" based on author rank, school rank, and journal rank. Match high-prestige articles to low-prestige articles with similar propensity scores but different title features. Compare citation outcomes within matched pairs.

This directly addresses the question: among articles with similar prestige profiles, do title features still predict impact?

### 7.5 Strategy 5: Natural Experiments and Instrumental Variables

These are aspirational and may not be feasible with available data, but they represent the gold standard for causal identification:

- **Title changes.** Some articles are posted on SSRN with one title and published in a journal with a different title. If we can identify such pairs, the SSRN-to-publication title change is exogenous to the article's content (assuming the content stayed roughly the same). Compare SSRN downloads before and after the title change.
- **Symposium randomization.** In symposium issues, authors are invited to contribute on a broad topic. The title is chosen by the author but the placement in a specific journal volume is not chosen by the author. Symposium articles provide partial randomization of the journal-title pairing.
- **Instrumental variable: editor characteristics.** If certain editorial boards have systematic title-editing practices (some student editors are known to request shorter titles), the editor cohort could serve as an instrument. This requires additional data on editorial boards and is a stretch goal.

### 7.6 Strategy 6: The Within-Author, Across-Journal Design

The most promising quasi-experimental design: identify authors who published articles in journals of similar rank in the same year, with different title characteristics. If author A published in two journals ranked 15-25 in 2020, one article with a colon-structured title and one without, the citation difference is attributable to something other than author prestige, journal prestige, or time.

This requires a large enough dataset that such pairs arise naturally. With 5,000+ articles, there should be hundreds of prolific-author pairs.


## 8. Validation Strategy

### 8.1 Train/Test Split

Before any analysis begins, randomly split the full dataset:

- **Training set (70%):** Used for all model estimation, feature selection, and hypothesis testing.
- **Test set (30%):** Held out, untouched until the final model is selected. Used once to report unbiased performance metrics.

The split is stratified by journal tier (Tiers 1-5) and publication year to ensure both sets are representative.

### 8.2 Cross-Validation (Within Training Set)

All model tuning (LASSO lambda, XGBoost hyperparameters) uses 10-fold cross-validation within the training set. Never use the test set for tuning.

### 8.3 Overfitting Diagnostics

- Compare training R-squared to cross-validated R-squared. If the gap exceeds 0.05, overfitting is likely.
- Track the number of features selected by LASSO across the 10 folds. If the selected features vary wildly across folds, the model is unstable.
- For tree-based models, compare training RMSE to out-of-bag RMSE.

### 8.4 External Validation (Stretch Goal)

After the main study, test the model on an out-of-sample dataset:

- **Time-based validation.** Collect 2024 articles (not in the original dataset). Apply the model trained on 2018-2023 data to 2024 titles and predict citations. Since 2024 articles have only 2 years of citation accumulation, use download counts as the primary DV.
- **Cross-disciplinary validation.** Test whether the model generalizes to non-law academic articles (e.g., economics or political science). If it does not, the findings are specific to the law review ecosystem, which is itself a contribution.


## 9. From Analysis to Formula

After the analysis is complete, the surviving features from LASSO regularization form the skeleton of a TEQ formula. The formula is constructed as follows:

1. Take the LASSO-selected features and their OLS coefficients from the final model (refit on the full training set without regularization, using only selected features).
2. Standardize the coefficients so they represent the relative importance of each feature.
3. Express the formula as a weighted linear combination: `TEQ = w1*f1 + w2*f2 + ... + wk*fk`, where w_i are the standardized coefficients and f_i are the selected features.
4. Optionally rescale to a 0-100 range for interpretability.

The formula is an output of the research, not an input. Its structure is unknown until the analysis is complete. It might have 5 features or 15. Length might matter or might not. Colons might matter or might not. The data decide.


## 10. Implementation Timeline

| Phase | Tasks | Duration | Deliverable |
|---|---|---|---|
| 1. Infrastructure | Set up repository, acquire W&L data, build Crossref scraper, pilot test on 3 journals | 3 weeks | Working pipeline, pilot dataset (~500 articles) |
| 2. Data collection | Scrape all target journals via Crossref; pull HeinOnline metadata; begin SSRN matching | 6 weeks | Raw dataset (~9,000 articles) |
| 3. Data cleaning | Filter to flagship articles, resolve author names, link to W&L baseline, construct author prestige variables | 3 weeks | Clean analysis-ready dataset |
| 4. Feature extraction | Run all title features through pipeline, QA manual audit on 10% sample | 2 weeks | Feature matrix |
| 5. Pre-registration | Finalize and timestamp hypothesis registry | 1 week | Hypothesis JSON file |
| 6. Analysis Stages 1-2 | Descriptive stats, univariate screening, hierarchical OLS | 3 weeks | Stage 1-2 results |
| 7. Analysis Stages 3-4 | LASSO/Elastic Net, Random Forest, XGBoost | 2 weeks | Feature selection results, model comparison |
| 8. Prestige controls | Journal fixed effects, PSM, within-author analysis | 3 weeks | Robustness results |
| 9. Test set evaluation | Apply final model to held-out 30% | 1 week | Unbiased performance metrics |
| 10. Writing | Draft article | 6 weeks | Manuscript |

Total: approximately 30 weeks from start to manuscript draft.


## 11. Technical Stack

| Component | Tool |
|---|---|
| Data collection | Python (requests, Crossref API client), Selenium/Playwright for SSRN |
| Data storage | SQLite or PostgreSQL; CSV exports for portability |
| Feature extraction | Python (spaCy, NLTK, TextBlob, scikit-learn TF-IDF) |
| Statistical analysis | R (lm, glmnet, lme4) or Python (statsmodels, scikit-learn) |
| Machine learning | Python (scikit-learn, XGBoost) |
| Visualization | R (ggplot2) or Python (matplotlib, seaborn) |
| Hypothesis registry | JSON file in Git repository, timestamped commits |
| Reproducibility | All code in version-controlled repository; random seeds fixed; analysis notebooks dated |


## 12. Ethical and Legal Considerations

- **Scraping terms of service.** Crossref explicitly permits API use. HeinOnline and SSRN ToS must be reviewed; institutional access through UNH library likely permits academic research use. Google Scholar's ToS prohibit automated access.
- **Author privacy.** All data are drawn from publicly available academic publications. No private information is collected. Author prestige proxies (h-index, school rank) are derived from public sources.
- **Normative implications.** The study could be misused to reduce title-writing to formula-following. The article should include a section discussing the limits of optimization and the value of creative, norm-breaking titles that the model cannot capture.
