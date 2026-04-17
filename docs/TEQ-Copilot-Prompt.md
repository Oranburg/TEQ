# TEQ Repository Scaffold — Copilot Prompt

## Mission

You are scaffolding a research repository called **TEQ** (Title Efficiency Quotient). This repo supports an empirical study on whether law review article titles predict placement and citation impact. The W&L Law Journal Rankings provide the baseline journal-level data. The study will collect article-level title and impact data, extract measurable features, and use statistical analysis to determine which features (if any) predict impact.

The principal investigator is Seth C. Oranburg, a law professor at UNH Franklin Pierce School of Law. This is academic research that will produce a publishable law review article. It is not a software product, not a startup tool, and not a dashboard.

## Critical Constraint: Hypothesis-Driven Science

The TEQ formula does not exist yet. It is the output of this research, not the input. You must scaffold a project that follows the scientific method:

1. Collect data
2. Extract features
3. Explore patterns
4. Form and test hypotheses
5. Build models from validated features
6. Write up results

If you find yourself building a scoring formula, stop. You are doing it wrong. The entire point of this repo is to discover whether such a formula is even possible, and if so, what it looks like.

---

## Phase Structure

### Phase 1: Data Collection
- W&L Law Journal Rankings data (5 CSV files) is already available and will be placed in `data/sources/`.
- Article-level data (titles, citation counts, placement tier, author info) needs to be collected. The collection methodology is TBD — the scaffold should include a loader for the W&L CSVs and stub scripts for future article-level data collection.

### Phase 2: Feature Extraction
- A deterministic NLP pipeline extracts measurable characteristics from article titles.
- Uses spaCy, regex, and dictionary lookups. No LLMs in v1.
- Features include things like word count, character count, colon presence, question mark presence, use of jargon, readability scores, etc.
- The module should define a clear interface (a function that takes a title string and returns a dict of features) with stub implementations.

### Phase 3: Exploratory Analysis
- Jupyter notebooks for visualizing distributions, correlations, and outliers.
- Plotly for interactive charts.
- No conclusions drawn at this stage — just pattern identification.

### Phase 4: Hypothesis Testing
- Every hypothesis must be pre-registered in the hypothesis registry before it is tested.
- Every test run must be logged with parameters, results, and timestamps.
- The Overseer module flags potential p-hacking (e.g., testing too many hypotheses without correction, cherry-picking results).

### Phase 5: Model Building
- Only after features have been empirically validated.
- OLS regression with controls (author prestige, journal rank, subject matter).
- Cross-validation to prevent overfitting.
- The "TEQ formula" (if one emerges) is the output of this phase.

### Phase 6: Validation and Paper Writing
- Out-of-sample validation.
- Robustness checks.
- The React dashboard (if built) belongs here, not earlier.
- Paper draft in LaTeX or Word.

---

## Repository Structure

Create the following directory structure:

```
TEQ/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── .gitignore
├── src/
│   └── teq/
│       ├── __init__.py
│       ├── models.py          # SQLAlchemy ORM models
│       ├── database.py        # DB engine, session, init
│       ├── features.py        # Feature extraction module
│       ├── hypothesis.py      # Hypothesis registry
│       ├── overseer.py        # Bias detection, p-hacking alerts
│       └── diary.py           # Research diary utilities
├── data/
│   ├── sources/               # Immutable source data (W&L CSVs go here)
│   │   └── .gitkeep
│   ├── collected/             # Raw collected article-level data
│   │   └── .gitkeep
│   └── processed/             # Cleaned, merged datasets
│       └── .gitkeep
├── notebooks/                 # Jupyter notebooks for exploration
│   └── .gitkeep
├── research/                  # Research diary entries (markdown)
│   └── 001_project-inception.md
├── scripts/
│   ├── load_wl_data.py        # Ingest W&L CSVs into SQLite
│   └── extract_features.py    # CLI script to run feature extraction
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_features.py
│   └── test_hypothesis.py
└── docs/
    └── .gitkeep
```

---

## pyproject.toml

Use a `[project]` table (PEP 621). Project name: `teq`. Python requires `>=3.11`. Dependencies:

```
pandas
spacy
scikit-learn
statsmodels
sqlalchemy
fastapi
pydantic
jupyter
plotly
pytest
httpx
```

Include a `[project.optional-dependencies]` section with `dev = ["pytest", "ruff", "mypy"]`.

---

## SQLAlchemy Models (`src/teq/models.py`)

Use SQLAlchemy 2.0 declarative style with `mapped_column`. All models inherit from a shared `Base`. Database is SQLite (file: `data/teq.db`).

### Journal
- `id`: Integer, primary key
- `wl_id`: String, unique (W&L identifier)
- `name`: String
- `rank`: Integer, nullable
- `combined_score`: Float, nullable
- `impact_factor`: Float, nullable
- `currency_score`: Float, nullable
- `category`: String, nullable (e.g., "General", "Specialty")
- `school`: String, nullable
- `created_at`: DateTime, default utcnow

### Article
- `id`: Integer, primary key
- `title`: String, not null
- `journal_id`: Integer, ForeignKey to Journal
- `year`: Integer
- `volume`: String, nullable
- `authors`: String, nullable (semicolon-delimited for v1)
- `citation_count`: Integer, nullable
- `placement_tier`: Integer, nullable (1-5 or similar)
- `doi`: String, nullable, unique
- `source`: String (where the data came from)
- `created_at`: DateTime, default utcnow

### TitleFeature
- `id`: Integer, primary key
- `article_id`: Integer, ForeignKey to Article
- `feature_name`: String, not null
- `feature_value`: Float, not null
- `extraction_version`: String (to track pipeline changes)
- `created_at`: DateTime, default utcnow
- Unique constraint on (article_id, feature_name, extraction_version)

### Hypothesis
- `id`: Integer, primary key
- `name`: String, unique
- `description`: Text
- `null_hypothesis`: Text
- `status`: String, default "registered" (registered, testing, confirmed, rejected, inconclusive)
- `registered_at`: DateTime, default utcnow
- `tested_at`: DateTime, nullable

### ExperimentRun
- `id`: Integer, primary key
- `hypothesis_id`: Integer, ForeignKey to Hypothesis, nullable
- `description`: Text
- `parameters`: Text (JSON string)
- `results`: Text (JSON string)
- `p_value`: Float, nullable
- `effect_size`: Float, nullable
- `notes`: Text, nullable
- `run_at`: DateTime, default utcnow

### AuditLog
- `id`: Integer, primary key
- `action`: String (e.g., "hypothesis_registered", "experiment_run", "data_loaded", "model_changed")
- `entity_type`: String, nullable
- `entity_id`: Integer, nullable
- `details`: Text (JSON string)
- `logged_at`: DateTime, default utcnow

---

## Database Module (`src/teq/database.py`)

- Create an `engine` using `sqlite:///data/teq.db` (relative path from repo root).
- Create a `SessionLocal` using `sessionmaker`.
- Provide an `init_db()` function that calls `Base.metadata.create_all(engine)`.
- Provide a `get_session()` context manager.

---

## Feature Extraction Module (`src/teq/features.py`)

Define an interface and implement only the simplest features. Leave the rest as stubs.

```python
def extract_features(title: str) -> dict[str, float]:
    """Extract measurable features from an article title.
    
    Returns a dict mapping feature names to numeric values.
    All features must be deterministic — same input always produces same output.
    """
```

Implement these features in v1:
- `word_count`: number of whitespace-delimited tokens
- `char_count`: total characters
- `has_colon`: 1.0 if title contains ":", else 0.0
- `has_question_mark`: 1.0 if title contains "?", else 0.0
- `has_subtitle`: 1.0 if title contains ":" or "—", else 0.0
- `title_case_ratio`: fraction of words that are title-cased (excluding articles/prepositions)

Leave these as stubs that return 0.0 with a `# TODO` comment:
- `flesch_reading_ease`
- `avg_word_length`
- `jargon_density`
- `novelty_score`
- `abstractness_score`
- `named_entity_count`
- `sentiment_polarity`
- `punctuation_density`

Also define:

```python
FEATURE_VERSION = "0.1.0"

def list_features() -> list[str]:
    """Return names of all implemented features."""

def list_stub_features() -> list[str]:
    """Return names of features not yet implemented."""
```

---

## Hypothesis Registry (`src/teq/hypothesis.py`)

Provide these functions:

```python
def register_hypothesis(name: str, description: str, null_hypothesis: str) -> Hypothesis:
    """Register a new hypothesis. Must be called BEFORE any testing."""

def list_hypotheses(status: str | None = None) -> list[Hypothesis]:
    """List all hypotheses, optionally filtered by status."""

def log_experiment(hypothesis_id: int | None, description: str, parameters: dict, results: dict, p_value: float | None = None, effect_size: float | None = None, notes: str | None = None) -> ExperimentRun:
    """Log an experiment run. Links to a hypothesis if provided."""

def update_hypothesis_status(hypothesis_id: int, new_status: str) -> Hypothesis:
    """Update hypothesis status after testing."""
```

All functions must also write to the AuditLog.

---

## Overseer Module (`src/teq/overseer.py`)

This module enforces research integrity. Implement:

```python
def check_hypothesis_registered(hypothesis_id: int) -> bool:
    """Verify a hypothesis was registered before any experiment references it."""

def check_multiple_comparisons(hypothesis_id: int, alpha: float = 0.05) -> dict:
    """Check if multiple experiments on the same hypothesis suggest p-hacking.
    Returns a dict with 'warning' key if the number of runs is suspicious."""

def check_experiment_logged(run_id: int) -> bool:
    """Verify an experiment run exists in the audit log."""

def generate_integrity_report() -> str:
    """Generate a plain-text report on research integrity:
    - Number of hypotheses by status
    - Number of experiment runs
    - Any warnings (unregistered tests, suspicious patterns)
    """
```

---

## W&L CSV Loader (`scripts/load_wl_data.py`)

Write a CLI script (use `argparse`) that:

1. Takes a directory path as argument (default: `data/sources/`).
2. Finds all `.csv` files in that directory.
3. Reads each CSV with pandas.
4. Maps columns to the Journal model fields (the exact column mapping will need adjustment — include a `COLUMN_MAP` dict at the top of the file that can be easily edited).
5. Inserts or updates Journal records (upsert by `wl_id` or `name`).
6. Logs the load action to AuditLog with count of records loaded.
7. Prints a summary to stdout.

Include a `COLUMN_MAP` like this, with a comment that it needs to be adjusted to match the actual CSV headers:

```python
# Adjust these mappings to match the actual W&L CSV column headers.
# Run `head -1 data/sources/*.csv` to see the actual headers.
COLUMN_MAP = {
    "Journal Name": "name",
    "Rank": "rank",
    "Combined Score": "combined_score",
    "Impact Factor": "impact_factor",
    # ... etc.
}
```

---

## Research Diary (`src/teq/diary.py` and `research/001_project-inception.md`)

The diary module should provide:

```python
def create_entry(title: str, content: str) -> str:
    """Create a new research diary entry as a markdown file in research/.
    Filename format: NNN_slugified-title.md
    Returns the file path.
    """

def list_entries() -> list[str]:
    """List all diary entries by filename."""
```

### Initial Diary Entry (`research/001_project-inception.md`)

Create this file with the following content:

```markdown
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
```

---

## CLAUDE.md

Create `CLAUDE.md` at the repo root with this content:

```markdown
# CLAUDE.md — TEQ Research Repository

## What This Is

TEQ (Title Efficiency Quotient) is an empirical research project studying whether law review article titles predict citation impact and placement tier. The principal investigator is Seth C. Oranburg.

This is a research project, not a product. There is no "user" other than the PI. There is no deployment target. The output is a law review article.

## Rules

1. **AI-generated content is never a source of truth.** The W&L CSV data and any collected article-level data are the sources of truth. AI tools help with analysis, not with facts.

2. **The W&L CSVs in `data/sources/` are immutable.** Never modify, overwrite, or "clean" the source files. Cleaning and transformation happen downstream in `data/processed/`.

3. **Every hypothesis must be pre-registered before testing.** Use `hypothesis.register_hypothesis()` before running any experiments against a hypothesis. The Overseer module checks for this.

4. **Every experiment run must be logged.** Use `hypothesis.log_experiment()` for every statistical test, model fit, or analytical result. No off-the-books analysis.

5. **The Overseer module must approve model changes.** Before changing the feature extraction pipeline or statistical model, run `overseer.generate_integrity_report()` and document the rationale in a research diary entry.

6. **The TEQ formula does not exist yet.** Do not implement, hardcode, or assume any formula. The formula is the output of Phase 5, not the input to Phase 1.

7. **No LLMs for feature extraction in v1.** Use deterministic NLP only (spaCy, regex, dictionary lookups). LLM-based features are a Phase 4 experiment that must be pre-registered like any other.

8. **Start simple.** SQLite, not PostgreSQL. CLI scripts, not API endpoints. Jupyter notebooks, not dashboards.

## Project Commands

```bash
# Initialize the database
python -c "from teq.database import init_db; init_db()"

# Load W&L data
python scripts/load_wl_data.py data/sources/

# Run tests
pytest tests/

# Generate integrity report
python -c "from teq.overseer import generate_integrity_report; print(generate_integrity_report())"
```

## Directory Layout

- `src/teq/` — Core Python package
- `data/sources/` — Immutable source data (W&L CSVs)
- `data/collected/` — Raw article-level data
- `data/processed/` — Cleaned datasets
- `notebooks/` — Jupyter exploration notebooks
- `research/` — Research diary entries
- `scripts/` — CLI utility scripts
- `tests/` — pytest test suite
- `docs/` — Documentation (sparse for now)
```

---

## README.md

Create a brief README:

```markdown
# TEQ: Title Efficiency Quotient

An empirical study of whether law review article titles predict citation impact and placement tier.

**PI:** Seth C. Oranburg, UNH Franklin Pierce School of Law

**Status:** Phase 1 — Data Collection and Infrastructure

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -c "from teq.database import init_db; init_db()"
```

## Research Question

Do measurable features of law review article titles predict citation impact and/or placement tier?

See `research/001_project-inception.md` for the full research plan.

See `CLAUDE.md` for repository rules and conventions.
```

---

## .gitignore

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
*.egg

# Data files over 50MB (tracked via DVC or LFS if needed)
*.parquet
*.feather

# Environment
.env
.env.*

# IDE
.vscode/
.idea/
*.swp
*.swo

# Jupyter
.ipynb_checkpoints/

# Database
data/teq.db

# Model artifacts
models/
*.pkl
*.joblib

# OS
.DS_Store
Thumbs.db

# Node (for future dashboard phase)
node_modules/
```

---

## Tests

### `tests/test_models.py`
- Test that `init_db()` creates all tables without error.
- Test creating a Journal, Article, and TitleFeature and reading them back.
- Test the unique constraint on TitleFeature (article_id, feature_name, extraction_version).

### `tests/test_features.py`
- Test `extract_features()` with known titles:
  - `"Corporations"` — word_count=1, has_colon=0, has_question_mark=0
  - `"Is Law Dead?: A Symposium"` — has_colon=1, has_question_mark=1
  - `"The Rise and Fall of Securities Regulation"` — word count=7, has_subtitle=0
- Test `list_features()` returns a non-empty list.
- Test that all implemented features return float values.

### `tests/test_hypothesis.py`
- Test registering a hypothesis and retrieving it.
- Test logging an experiment and linking it to a hypothesis.
- Test that the audit log records both actions.
- Test `list_hypotheses()` with status filter.

---

## Anti-Patterns — Do NOT Do These

1. **Do NOT build a frontend, dashboard, or web UI.** That is Phase 6. The scaffold is CLI and notebooks only.

2. **Do NOT implement a TEQ formula or scoring algorithm.** There is no formula. The formula is what the research aims to discover. If you create a function called `calculate_teq_score()` or anything similar, you have failed.

3. **Do NOT use LLMs, GPT, or any generative AI for feature extraction.** v1 uses spaCy, regex, and dictionary lookups only. LLM features are a future experiment.

4. **Do NOT over-engineer the infrastructure.** SQLite, not PostgreSQL. No Docker. No CI/CD. No deployment configs. No Kubernetes. No cloud services.

5. **Do NOT create FastAPI endpoints.** FastAPI is a dependency for a future phase. The scaffold should not include any `app = FastAPI()` code or route definitions.

6. **Do NOT modify or "clean" files in `data/sources/`.** Those are immutable. All transformations go to `data/processed/`.

7. **Do NOT generate synthetic data or sample articles.** The tests should use hardcoded title strings, not generated datasets.

8. **Do NOT add a "default" or "example" TEQ calculation anywhere.** Not in notebooks, not in scripts, not in tests. The research has not been done yet.

---

## Summary of What to Build

You are creating a clean, minimal Python research scaffold. When you are done, the repo should:

1. Install cleanly with `pip install -e .`
2. Initialize an empty SQLite database with 6 tables
3. Load W&L CSV data into the Journal table (with an adjustable column mapping)
4. Extract 6 simple title features from any string, with 8 more stubbed out
5. Register hypotheses and log experiments with full audit trails
6. Flag potential research integrity issues
7. Have a research diary with one initial entry documenting the research plan
8. Pass all tests
9. Contain clear documentation (CLAUDE.md, README.md) that embeds the scientific process into the repo itself

Nothing more. Nothing less.
