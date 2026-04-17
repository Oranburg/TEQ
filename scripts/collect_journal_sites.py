"""Scrape article metadata from law review websites.

Many law reviews publish full tables of contents on their websites.
This script handles common site patterns. Not every journal will work —
some use Cloudflare or other bot protection (403 errors).

Usage:
    python scripts/collect_journal_sites.py --test          # test which sites respond
    python scripts/collect_journal_sites.py --scrape        # scrape all accessible sites
    python scripts/collect_journal_sites.py --journal "Fordham Law Review"

This is a best-effort collector. For comprehensive data, use HeinOnline exports.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx

from teq.database import get_session, init_db
from teq.models import Article, AuditLog, Journal

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


@dataclass
class SiteConfig:
    """Configuration for scraping a specific journal's website."""
    journal_name: str
    archive_url: str
    # CSS-like selectors described as regex patterns for title extraction
    title_pattern: str = r'<h[1-4][^>]*class="[^"]*(?:entry-title|article-title|post-title)[^"]*"[^>]*>(.*?)</h[1-4]>'
    # Fallback: any heading that looks like an article title
    fallback_pattern: str = r'<h[1-4][^>]*>(.*?)</h[1-4]>'
    # Pattern to find author names near titles
    author_pattern: str = r'(?:by|By|BY)\s+([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+)*)'
    # Volume/issue page URLs to iterate
    volume_url_template: str | None = None
    min_volume: int = 90
    max_volume: int = 95


# Known journal site configurations.
# Add new journals here as we discover their URL patterns.
KNOWN_SITES: list[SiteConfig] = [
    # --- Original 3 ---
    SiteConfig(
        journal_name="Fordham Law Review",
        archive_url="https://fordhamlawreview.org/issues/",
    ),
    SiteConfig(
        journal_name="Boston University Law Review",
        archive_url="https://www.bu.edu/bulawreview/archives/",
    ),
    SiteConfig(
        journal_name="Iowa Law Review",
        archive_url="https://ilr.law.uiowa.edu/online/",
    ),
    # --- Discovered 2026-04-16: top-50 journals with accessible sites ---
    SiteConfig(
        journal_name="Harvard Law Review",
        archive_url="https://harvardlawreview.org/",
    ),
    SiteConfig(
        journal_name="Yale Law Journal",
        archive_url="https://www.yalelawjournal.org/issue",
    ),
    SiteConfig(
        journal_name="University of Pennsylvania Law Review",
        archive_url="https://scholarship.law.upenn.edu/penn_law_review/",
    ),
    SiteConfig(
        journal_name="University of Chicago Law Review",
        archive_url="https://chicagounbound.uchicago.edu/uclrev/",
    ),
    SiteConfig(
        journal_name="Duke Law Journal",
        archive_url="https://dlj.law.duke.edu/",
    ),
    SiteConfig(
        journal_name="New York University Law Review",
        archive_url="https://nyulawreview.org/",
    ),
    SiteConfig(
        journal_name="Minnesota Law Review",
        archive_url="https://www.minnesotalawreview.org/",
    ),
    SiteConfig(
        journal_name="Northwestern University Law Review",
        archive_url="https://scholarlycommons.law.northwestern.edu/nulr/",
    ),
    SiteConfig(
        journal_name="Texas Law Review",
        archive_url="https://www.texaslawreview.org/",
    ),
    SiteConfig(
        journal_name="UCLA Law Review",
        archive_url="https://www.uclalawreview.org/",
    ),
    SiteConfig(
        journal_name="Boston College Law Review",
        archive_url="https://bclawreview.org/",
    ),
    SiteConfig(
        journal_name="Southern California Law Review",
        archive_url="https://southerncalifornialawreview.com/",
    ),
    SiteConfig(
        journal_name="George Washington Law Review",
        archive_url="https://www.gwlr.org/",
    ),
    SiteConfig(
        journal_name="University of Illinois Law Review",
        archive_url="https://illinoislawreview.org/",
    ),
    SiteConfig(
        journal_name="Washington Law Review",
        archive_url="https://washingtonlawreview.org/",
    ),
    SiteConfig(
        journal_name="Wisconsin Law Review",
        archive_url="https://wlr.law.wisc.edu/",
    ),
    SiteConfig(
        journal_name="William & Mary Law Review",
        archive_url="https://scholarship.law.wm.edu/wmlr/",
    ),
    SiteConfig(
        journal_name="North Carolina Law Review",
        archive_url="https://scholarship.law.unc.edu/nclr/",
    ),
    SiteConfig(
        journal_name="UC Law Journal",
        archive_url="https://uclawreview.org/",
    ),
    SiteConfig(
        journal_name="Harvard Journal of Law & Technology",
        archive_url="https://jolt.law.harvard.edu/",
    ),
    SiteConfig(
        journal_name="Administrative Law Review",
        archive_url="https://www.administrativelawreview.org/",
    ),
    SiteConfig(
        journal_name="Arizona Law Review",
        archive_url="https://arizonalawreview.org/",
    ),
]


def clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_titles_from_html(html: str, config: SiteConfig) -> list[dict]:
    """Extract article titles and authors from HTML content."""
    articles = []

    # Try specific pattern first, then fallback
    for pattern in [config.title_pattern, config.fallback_pattern]:
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        for match in matches:
            title = clean_html(match)

            # Filter out non-article content
            if len(title) < 15:
                continue
            if title.lower() in ('archives', 'issues', 'about', 'contact',
                                  'submit', 'masthead', 'subscribe',
                                  'join our mailing list', 'share this:',
                                  'archives: issues'):
                continue
            # Skip if it looks like a navigation element
            if any(skip in title.lower() for skip in
                   ['menu', 'search', 'copyright', 'privacy', 'log in',
                    'sign up', 'newsletter', 'mailing list', 'widget']):
                continue

            articles.append({
                "title": title,
                "authors": None,
                "source": "journal_website",
            })

        # If we found articles with the first pattern, don't use fallback
        if articles:
            break

    # Try to extract authors
    for art in articles:
        # Look for author pattern near the title in the HTML
        title_pos = html.lower().find(art["title"].lower()[:30])
        if title_pos >= 0:
            # Search in the 500 chars after the title
            nearby = html[title_pos:title_pos + 500]
            author_match = re.search(config.author_pattern, nearby)
            if author_match:
                art["authors"] = author_match.group(1).strip()

    return articles


def test_sites() -> None:
    """Test which journal websites are accessible."""
    print("Testing journal website accessibility...\n")

    with get_session() as session:
        journals = session.query(Journal).order_by(Journal.rank).all()

        # Build a rough URL guess for each journal
        accessible = 0
        blocked = 0
        not_found = 0

        # Test known sites first
        print("Known site configurations:")
        for config in KNOWN_SITES:
            try:
                resp = httpx.get(config.archive_url, headers=HEADERS,
                               timeout=15, follow_redirects=True)
                articles = extract_titles_from_html(resp.text, config)
                print(f"  {config.journal_name}: {resp.status_code} | "
                      f"{len(articles)} titles found")
                accessible += 1
            except Exception as e:
                print(f"  {config.journal_name}: ERROR {e}")
                blocked += 1

        print(f"\nAccessible: {accessible} | Blocked: {blocked}")


def scrape_known_sites() -> None:
    """Scrape all known accessible journal sites."""
    init_db()

    with get_session() as session:
        total_stored = 0

        for config in KNOWN_SITES:
            # Find journal in DB
            journal = (
                session.query(Journal)
                .filter(Journal.name.ilike(f"%{config.journal_name}%"))
                .first()
            )
            if not journal:
                print(f"  SKIP {config.journal_name}: not in database")
                continue

            print(f"  Scraping {config.journal_name}...", end=" ", flush=True)

            try:
                resp = httpx.get(config.archive_url, headers=HEADERS,
                               timeout=15, follow_redirects=True)
                if resp.status_code != 200:
                    print(f"HTTP {resp.status_code}")
                    continue

                articles = extract_titles_from_html(resp.text, config)
                stored = 0

                for art in articles:
                    # Check for duplicate
                    existing = (
                        session.query(Article)
                        .filter_by(title=art["title"], journal_id=journal.id)
                        .first()
                    )
                    if existing:
                        continue

                    article = Article(
                        title=art["title"],
                        journal_id=journal.id,
                        authors=art["authors"],
                        source="journal_website",
                    )
                    session.add(article)
                    stored += 1

                total_stored += stored
                print(f"found {len(articles)}, stored {stored} new")

            except Exception as e:
                print(f"ERROR: {e}")

            time.sleep(2)  # Be polite

        log = AuditLog(
            action="journal_site_scrape",
            entity_type="Article",
            details=json.dumps({"total_stored": total_stored}),
        )
        session.add(log)

    print(f"\nDone. Total new articles stored: {total_stored}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape article data from law review websites."
    )
    parser.add_argument("--test", action="store_true",
                       help="Test which sites are accessible")
    parser.add_argument("--scrape", action="store_true",
                       help="Scrape all known accessible sites")
    parser.add_argument("--journal", type=str, default=None,
                       help="Scrape a specific journal by name")
    args = parser.parse_args()

    if args.test:
        test_sites()
    elif args.scrape:
        scrape_known_sites()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
