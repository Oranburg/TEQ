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
# Adjust these mappings to match the actual W&L CSV column headers.
# Run `head -1 data/sources/*.csv` to see the actual headers.
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    "Journal Name": "name",
    "Rank": "rank",
    "Combined Score": "combined_score",
    "Impact Factor": "impact_factor",
    "Currency Score": "currency_score",
    "Category": "category",
    "School": "school",
    "WL ID": "wl_id",
}


def _coerce_float(value) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _coerce_int(value) -> int | None:
    try:
        return int(value)
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
            continue  # skip rows without a journal name

        wl_id = row.get("wl_id")
        if wl_id is None or pd.isna(wl_id):
            wl_id = None

        # Look for an existing record by wl_id or name.
        existing = None
        if wl_id:
            existing = session.query(Journal).filter_by(wl_id=wl_id).first()
        if existing is None:
            existing = session.query(Journal).filter_by(name=str(name)).first()

        if existing is None:
            journal = Journal()
            session.add(journal)
        else:
            journal = existing

        journal.name = str(name)
        if wl_id:
            journal.wl_id = str(wl_id)
        journal.rank = _coerce_int(row.get("rank"))
        journal.combined_score = _coerce_float(row.get("combined_score"))
        journal.impact_factor = _coerce_float(row.get("impact_factor"))
        journal.currency_score = _coerce_float(row.get("currency_score"))
        category = row.get("category")
        if category and not pd.isna(category):
            journal.category = str(category)
        school = row.get("school")
        if school and not pd.isna(school):
            journal.school = str(school)

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
