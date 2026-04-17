"""Process HeinOnline CSV exports into the TEQ database.

HeinOnline requires institutional access. The workflow is:
1. Log into HeinOnline via your university
2. Use ScholarCheck or Law Journal Library search
3. Export results as CSV
4. Run this script to import

Usage:
    python scripts/process_heinonline.py path/to/export.csv
    python scripts/process_heinonline.py data/collected/hein_*.csv

Expected CSV columns (HeinOnline export format):
    Title, Author, Journal, Volume, Date, First Page, Citation Count
    (Column names may vary; the COLUMN_MAP below handles common variants)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from teq.database import get_session, init_db
from teq.models import Article, AuditLog, Journal

# HeinOnline exports use various column names across different export types.
# Map common variants to our internal field names.
COLUMN_MAP = {
    # Title variants
    "Title": "title",
    "Article Title": "title",
    "title": "title",
    # Author variants
    "Author": "authors",
    "Authors": "authors",
    "author": "authors",
    # Journal variants
    "Journal": "journal_name",
    "Publication": "journal_name",
    "Source": "journal_name",
    "journal": "journal_name",
    # Year/Date variants
    "Date": "year",
    "Year": "year",
    "Publication Date": "year",
    "Pub. Date": "year",
    # Citation count variants
    "Citation Count": "citation_count",
    "Citations": "citation_count",
    "Times Cited": "citation_count",
    "ScholarCheck Count": "citation_count",
    # Volume
    "Volume": "volume",
    "Vol.": "volume",
    # Page
    "First Page": "first_page",
    "Page": "first_page",
    "Starting Page": "first_page",
}


def extract_year(value) -> int | None:
    """Extract a 4-digit year from various date formats."""
    if pd.isna(value):
        return None
    s = str(value)
    match = re.search(r"(19|20)\d{2}", s)
    if match:
        return int(match.group())
    return None


def match_journal(name: str, session) -> Journal | None:
    """Try to match a HeinOnline journal name to our database."""
    if not name or pd.isna(name):
        return None
    name = str(name).strip()

    # Exact match
    j = session.query(Journal).filter_by(name=name).first()
    if j:
        return j

    # Try case-insensitive
    j = session.query(Journal).filter(Journal.name.ilike(name)).first()
    if j:
        return j

    # Try contains (for abbreviation mismatches)
    j = session.query(Journal).filter(Journal.name.ilike(f"%{name}%")).first()
    if j:
        return j

    return None


def process_csv(path: Path, session) -> dict:
    """Process a single HeinOnline CSV export. Returns stats dict."""
    df = pd.read_csv(path, dtype=str)

    # Apply column mapping
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "title" not in df.columns:
        return {"file": str(path), "error": "No title column found", "stored": 0}

    stored = 0
    skipped_no_journal = 0
    skipped_duplicate = 0
    skipped_short = 0

    for _, row in df.iterrows():
        title = row.get("title")
        if not title or pd.isna(title):
            continue
        title = str(title).strip()

        # Skip very short titles (editorials, TOC, etc.)
        if len(title) < 15:
            skipped_short += 1
            continue

        # Match journal
        journal_name = row.get("journal_name")
        journal = match_journal(journal_name, session) if journal_name else None
        if journal is None:
            skipped_no_journal += 1
            continue

        year = extract_year(row.get("year"))

        # Check for duplicate
        existing = (
            session.query(Article)
            .filter_by(title=title, journal_id=journal.id, year=year)
            .first()
        )
        if existing:
            # Update citation count if we have a newer one from HeinOnline
            hein_count = row.get("citation_count")
            if hein_count and not pd.isna(hein_count):
                try:
                    existing.citation_count = int(float(hein_count))
                except (ValueError, TypeError):
                    pass
            skipped_duplicate += 1
            continue

        # Parse citation count
        citation_count = None
        cc = row.get("citation_count")
        if cc and not pd.isna(cc):
            try:
                citation_count = int(float(cc))
            except (ValueError, TypeError):
                pass

        article = Article(
            title=title,
            journal_id=journal.id,
            year=year,
            volume=row.get("volume") if not pd.isna(row.get("volume", float("nan"))) else None,
            authors=row.get("authors") if not pd.isna(row.get("authors", float("nan"))) else None,
            citation_count=citation_count,
            source="heinonline",
        )
        session.add(article)
        stored += 1

    return {
        "file": str(path),
        "stored": stored,
        "skipped_no_journal": skipped_no_journal,
        "skipped_duplicate": skipped_duplicate,
        "skipped_short": skipped_short,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import HeinOnline CSV exports into TEQ database."
    )
    parser.add_argument("files", nargs="+", help="CSV file(s) to process")
    args = parser.parse_args()

    init_db()

    all_stats = []
    total_stored = 0

    with get_session() as session:
        for file_arg in args.files:
            for path in sorted(Path(".").glob(file_arg)) if "*" in file_arg else [Path(file_arg)]:
                if not path.exists():
                    print(f"  SKIP: {path} not found")
                    continue
                print(f"  Processing {path.name}...", end=" ", flush=True)
                stats = process_csv(path, session)
                all_stats.append(stats)
                total_stored += stats.get("stored", 0)
                print(
                    f"stored {stats['stored']}, "
                    f"no-journal {stats.get('skipped_no_journal', 0)}, "
                    f"dupes {stats.get('skipped_duplicate', 0)}"
                )

        log = AuditLog(
            action="heinonline_import",
            entity_type="Article",
            details=json.dumps({
                "files": [s["file"] for s in all_stats],
                "total_stored": total_stored,
            }),
        )
        session.add(log)

    print(f"\nDone. Total new articles stored: {total_stored}")


if __name__ == "__main__":
    main()
