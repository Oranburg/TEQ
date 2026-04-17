"""Collect citation data and author profiles from Google Scholar.

Google Scholar has no official API and actively blocks automated scraping.
This script uses the `scholarly` library which handles rate limiting and
proxy rotation, but it is fragile and slow by design.

Use this as a VALIDATION source, not a primary collector.
Primary data should come from Crossref and HeinOnline.

Usage:
    python scripts/collect_scholar.py --author "Seth Oranburg"
    python scripts/collect_scholar.py --sample 100      # random 100 articles from DB
    python scripts/collect_scholar.py --journal "Harvard Law Review" --year 2022

Requirements:
    pip install scholarly
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    from scholarly import scholarly
except ImportError:
    print("ERROR: Install scholarly first: pip install scholarly", file=sys.stderr)
    sys.exit(1)

from sqlalchemy import func

from teq.database import get_session, init_db
from teq.models import Article, AuditLog, Journal


def search_author(name: str) -> dict | None:
    """Look up an author on Google Scholar and return profile data."""
    try:
        results = scholarly.search_author(name)
        author = next(results, None)
        if author is None:
            return None

        # Fill in full profile
        author = scholarly.fill(author)

        return {
            "name": author.get("name"),
            "affiliation": author.get("affiliation"),
            "interests": author.get("interests", []),
            "citedby": author.get("citedby"),
            "h_index": author.get("hindex"),
            "i10_index": author.get("i10index"),
            "scholar_id": author.get("scholar_id"),
            "num_publications": len(author.get("publications", [])),
        }
    except Exception as e:
        print(f"    Error searching for {name}: {e}")
        return None


def search_article_citations(title: str) -> int | None:
    """Look up an article by title and return its Google Scholar citation count."""
    try:
        results = scholarly.search_pubs(title)
        pub = next(results, None)
        if pub is None:
            return None

        # Verify title is a close match (Scholar returns fuzzy results)
        found_title = pub.get("bib", {}).get("title", "")
        if not found_title:
            return None

        # Simple similarity check: at least 60% word overlap
        title_words = set(title.lower().split())
        found_words = set(found_title.lower().split())
        if len(title_words) == 0:
            return None
        overlap = len(title_words & found_words) / len(title_words)
        if overlap < 0.6:
            return None

        return pub.get("num_citations")
    except Exception as e:
        print(f"    Error searching for '{title[:50]}...': {e}")
        return None


def collect_for_sample(sample_size: int) -> None:
    """Collect Google Scholar citation counts for a random sample of articles."""
    init_db()

    with get_session() as session:
        # Get random sample of articles that don't have Scholar data yet
        articles = (
            session.query(Article)
            .filter(Article.source != "scholar_validated")
            .order_by(func.random())
            .limit(sample_size)
            .all()
        )

        if not articles:
            print("No articles available for sampling.")
            return

        print(f"Sampling {len(articles)} articles for Google Scholar validation...")
        updated = 0
        not_found = 0

        for i, art in enumerate(articles):
            print(f"  [{i+1}/{len(articles)}] {art.title[:60]}...", end=" ", flush=True)
            gs_count = search_article_citations(art.title)

            if gs_count is not None:
                # Store Scholar count in notes or a separate field
                # For now, update citation_count if Scholar has a higher count
                if art.citation_count is None or gs_count > art.citation_count:
                    art.citation_count = gs_count
                updated += 1
                print(f"citations={gs_count}")
            else:
                not_found += 1
                print("not found")

            # Scholar rate limit: be very conservative
            time.sleep(3 + (i % 5))  # 3-8 seconds between requests

        log = AuditLog(
            action="scholar_validation",
            entity_type="Article",
            details=json.dumps({
                "sample_size": len(articles),
                "updated": updated,
                "not_found": not_found,
            }),
        )
        session.add(log)

    print(f"\nDone. Updated: {updated}, Not found: {not_found}")


def lookup_author(name: str) -> None:
    """Look up a single author and print their profile."""
    print(f"Searching Google Scholar for: {name}")
    profile = search_author(name)

    if profile is None:
        print("  Not found.")
        return

    print(f"  Name: {profile['name']}")
    print(f"  Affiliation: {profile.get('affiliation', 'N/A')}")
    print(f"  Interests: {', '.join(profile.get('interests', []))}")
    print(f"  Total citations: {profile.get('citedby', 'N/A')}")
    print(f"  h-index: {profile.get('h_index', 'N/A')}")
    print(f"  i10-index: {profile.get('i10_index', 'N/A')}")
    print(f"  Publications: {profile.get('num_publications', 'N/A')}")
    print(f"  Scholar ID: {profile.get('scholar_id', 'N/A')}")

    # Save to data/collected for later use
    out_path = Path("data/collected") / f"scholar_author_{name.replace(' ', '_').lower()}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profile, indent=2))
    print(f"\n  Saved to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect data from Google Scholar (validation source)."
    )
    parser.add_argument(
        "--author", type=str, default=None,
        help="Look up an author profile by name"
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Validate citation counts for N random articles from the DB"
    )
    args = parser.parse_args()

    if args.author:
        lookup_author(args.author)
    elif args.sample:
        collect_for_sample(args.sample)
    else:
        parser.print_help()
        print("\nSpecify --author or --sample to collect data.")


if __name__ == "__main__":
    main()
