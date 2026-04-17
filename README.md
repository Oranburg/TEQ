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
