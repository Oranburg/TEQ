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
