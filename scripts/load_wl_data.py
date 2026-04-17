"""CLI script to load W&L Law Journal Rankings CSV files into the TEQ database.

Usage:
    python scripts/load_wl_data.py [--dir data/sources/]

The script reads every .csv file in the given directory, maps columns to
Journal model fields using COLUMN_MAP, and upserts records into the database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from teq.database import get_session, init_db
from teq.models import AuditLog, Journal

# ---------------------------------------------------------------------------
# Column mapping for the 2024-LawJ-Master.csv format.
# The W&L export has a blank header for the journal name column.
# Our enriched master CSV uses these headers:
#   rank, name, combined, impact, journals, currency, cases, scope, editing, format
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "rank": "rank",
    "name": "name",
    "combined": "combined_score",
    "impact": "impact_factor",
    "journals": "journals_cited",
    "currency": "currency_score",
    "cases": "cases_cited",
    "scope": "scope",
    "editing": "editing",
    "format": "format",
}


def _coerce_float(value) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _coerce_int(value) -> int | None:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def load_csv(path: Path, session) -> int:
    """Load a single CSV file and upsert Journal records. Returns count loaded."""
    df = pd.read_csv(path, dtype=str)

    # Apply column mapping — only keep columns present in both the CSV and COLUMN_MAP.
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    loaded = 0
    for _, row in df.iterrows():
        name = row.get("name")
        if not name or pd.isna(name):
            continue

        # Look for an existing record by name.
        existing = session.query(Journal).filter_by(name=str(name)).first()

        if existing is None:
            journal = Journal()
            session.add(journal)
        else:
            journal = existing

        journal.name = str(name)
        journal.rank = _coerce_int(row.get("rank"))
        journal.combined_score = _coerce_float(row.get("combined_score"))
        journal.impact_factor = _coerce_float(row.get("impact_factor"))
        journal.journals_cited = _coerce_int(row.get("journals_cited"))
        journal.currency_score = _coerce_float(row.get("currency_score"))
        journal.cases_cited = _coerce_int(row.get("cases_cited"))

        scope = row.get("scope")
        if scope and not pd.isna(scope):
            journal.scope = str(scope)
        editing = row.get("editing")
        if editing and not pd.isna(editing):
            journal.editing = str(editing)
        fmt = row.get("format")
        if fmt and not pd.isna(fmt):
            journal.format = str(fmt)

        loaded += 1

    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load W&L Law Journal Rankings CSV files into the TEQ database."
    )
    parser.add_argument(
        "--dir",
        default="data/sources/",
        help="Directory containing W&L CSV files (default: data/sources/)",
    )
    args = parser.parse_args()

    source_dir = Path(args.dir)
    if not source_dir.exists():
        print(f"ERROR: Directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    csv_files = sorted(source_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {source_dir}.")
        sys.exit(0)

    init_db()

    total_loaded = 0
    file_summaries: list[dict] = []

    with get_session() as session:
        for csv_path in csv_files:
            count = load_csv(csv_path, session)
            total_loaded += count
            file_summaries.append({"file": str(csv_path), "records": count})
            print(f"  Loaded {count} records from {csv_path.name}")

        # Write audit log entry.
        log = AuditLog(
            action="data_loaded",
            entity_type="Journal",
            entity_id=None,
            details=json.dumps(
                {"files": [s["file"] for s in file_summaries], "total": total_loaded}
            ),
        )
        session.add(log)

    print(f"\nDone. Total records loaded/updated: {total_loaded}")


if __name__ == "__main__":
    main()
