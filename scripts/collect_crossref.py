"""Collect article metadata from Crossref API for journals in the TEQ database.

Usage:
    python scripts/collect_crossref.py                    # all journals
    python scripts/collect_crossref.py --limit 5          # first 5 journals
    python scripts/collect_crossref.py --journal "Harvard Law Review"
    python scripts/collect_crossref.py --tier 1           # top 14 only

Crossref API is free, no key required. We use polite pool by providing
a mailto in the User-Agent header.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from teq.database import get_session, init_db
from teq.models import Article, AuditLog, Journal

# Polite pool: Crossref gives faster responses if you identify yourself.
# Replace with PI's email.
MAILTO = "seth@oranburg.law"
BASE_URL = "https://api.crossref.org/works"
HEADERS = {"User-Agent": f"TEQ-Research/0.1 (mailto:{MAILTO})"}

# Filter to law review content types
VALID_TYPES = {"journal-article"}

# Years to collect
MIN_YEAR = 2018
MAX_YEAR = 2024


def resolve_issn(journal_name: str) -> str | None:
    """Look up a journal's ISSN via the Crossref journals endpoint."""
    try:
        resp = httpx.get(
            "https://api.crossref.org/journals",
            params={"query": journal_name, "rows": 5, "mailto": MAILTO},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        for item in items:
            # Match: title must be very close to our journal name
            cr_title = item.get("title", "").lower().strip()
            jn_lower = journal_name.lower().strip()
            if cr_title == jn_lower or jn_lower in cr_title or cr_title in jn_lower:
                issns = item.get("ISSN", [])
                if issns:
                    return issns[0]
    except Exception:
        pass
    return None


def fetch_articles_for_journal(
    journal_name: str, rows_per_page: int = 50, max_pages: int = 10
) -> list[dict]:
    """Query Crossref for articles from a specific journal.

    First resolves the journal's ISSN, then queries by ISSN for precise results.
    Falls back to container-title search if ISSN not found.
    """
    issn = resolve_issn(journal_name)

    articles = []
    cursor = "*"

    for page in range(max_pages):
        params = {
            "filter": f"from-pub-date:{MIN_YEAR},until-pub-date:{MAX_YEAR},type:journal-article",
            "select": "DOI,title,author,published-print,published-online,volume,is-referenced-by-count,container-title,type",
            "rows": rows_per_page,
            "cursor": cursor,
            "mailto": MAILTO,
        }

        if issn:
            # ISSN-based query: precise, no fuzzy matching needed
            params["filter"] += f",issn:{issn}"
        else:
            # Fallback: container-title search (fuzzy)
            params["query.container-title"] = journal_name

        try:
            resp = httpx.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"    HTTP error on page {page + 1}: {e}")
            break

        data = resp.json()
        items = data.get("message", {}).get("items", [])

        if not items:
            break

        for item in items:
            # If no ISSN, verify container title matches
            if not issn:
                container = item.get("container-title", [])
                if not container:
                    continue
                container_name = container[0] if isinstance(container, list) else container
                cn_lower = container_name.lower().strip()
                jn_lower = journal_name.lower().strip()
                if cn_lower != jn_lower and jn_lower not in cn_lower and cn_lower not in jn_lower:
                    continue

            title_list = item.get("title", [])
            if not title_list:
                continue
            title = title_list[0]

            # Skip very short titles (likely editorials, TOC, errata)
            if len(title) < 15:
                continue

            # Extract year from published-print or published-online
            year = None
            for date_field in ["published-print", "published-online"]:
                date_parts = item.get(date_field, {}).get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    year = date_parts[0][0]
                    break

            if year is None or year < MIN_YEAR or year > MAX_YEAR:
                continue

            # Extract authors
            authors_raw = item.get("author", [])
            author_names = []
            for a in authors_raw:
                given = a.get("given", "")
                family = a.get("family", "")
                if family:
                    author_names.append(f"{given} {family}".strip())
            authors_str = "; ".join(author_names) if author_names else None

            articles.append({
                "title": title,
                "authors": authors_str,
                "year": year,
                "volume": item.get("volume"),
                "doi": item.get("DOI"),
                "citation_count": item.get("is-referenced-by-count", 0),
                "source": "crossref",
            })

        # Get next cursor
        cursor = data.get("message", {}).get("next-cursor")
        if not cursor:
            break

        # Rate limit: be polite
        time.sleep(0.5)

    return articles


def store_articles(journal_id: int, articles: list[dict], session) -> int:
    """Store articles in the database, skipping duplicates by DOI or title+year."""
    stored = 0
    for art in articles:
        # Check for duplicate by DOI
        if art["doi"]:
            existing = session.query(Article).filter_by(doi=art["doi"]).first()
            if existing:
                continue

        # Check for duplicate by title + journal + year
        existing = (
            session.query(Article)
            .filter_by(title=art["title"], journal_id=journal_id, year=art["year"])
            .first()
        )
        if existing:
            continue

        article = Article(
            title=art["title"],
            journal_id=journal_id,
            year=art["year"],
            volume=art["volume"],
            authors=art["authors"],
            citation_count=art["citation_count"],
            doi=art["doi"],
            source=art["source"],
        )
        session.add(article)
        stored += 1

    return stored


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect article data from Crossref API."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max number of journals to process"
    )
    parser.add_argument(
        "--journal", type=str, default=None, help="Process a single journal by name"
    )
    parser.add_argument(
        "--tier", type=int, default=None,
        help="Process journals in a rank tier: 1=top14, 2=15-50, 3=51-150, 4=151-400"
    )
    parser.add_argument(
        "--max-pages", type=int, default=10,
        help="Max Crossref API pages per journal (default: 10, ~500 articles)"
    )
    args = parser.parse_args()

    init_db()

    with get_session() as session:
        query = session.query(Journal).order_by(Journal.rank)

        if args.journal:
            query = query.filter(Journal.name.ilike(f"%{args.journal}%"))
        elif args.tier:
            tier_ranges = {1: (1, 14), 2: (15, 50), 3: (51, 150), 4: (151, 400)}
            if args.tier not in tier_ranges:
                print(f"Invalid tier {args.tier}. Use 1-4.", file=sys.stderr)
                sys.exit(1)
            lo, hi = tier_ranges[args.tier]
            query = query.filter(Journal.rank >= lo, Journal.rank <= hi)

        if args.limit:
            query = query.limit(args.limit)

        journals = query.all()

        if not journals:
            print("No journals found matching criteria.")
            sys.exit(0)

        print(f"Collecting articles for {len(journals)} journals...")
        print(f"Year range: {MIN_YEAR}-{MAX_YEAR}")
        print()

        total_stored = 0
        for j in journals:
            print(f"  #{j.rank} {j.name}...", end=" ", flush=True)
            articles = fetch_articles_for_journal(
                j.name, max_pages=args.max_pages
            )
            stored = store_articles(j.id, articles, session)
            total_stored += stored
            print(f"found {len(articles)}, stored {stored} new")

            # Rate limit between journals
            time.sleep(1)

        # Audit log
        log = AuditLog(
            action="crossref_collection",
            entity_type="Article",
            details=json.dumps({
                "journals_queried": len(journals),
                "articles_stored": total_stored,
                "year_range": f"{MIN_YEAR}-{MAX_YEAR}",
            }),
        )
        session.add(log)

    print(f"\nDone. Total new articles stored: {total_stored}")


if __name__ == "__main__":
    main()
