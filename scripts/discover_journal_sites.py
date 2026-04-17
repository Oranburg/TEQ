"""Discover scrapable law review journal websites.

Probes common URL patterns for top-ranked journals and reports which
sites return 200 with article-like content.

Usage:
    PYTHONPATH=src python3 scripts/discover_journal_sites.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx
from teq.database import get_session
from teq.models import Journal

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# Title-like patterns in HTML
ARTICLE_TITLE_RE = re.compile(
    r'<h[1-4][^>]*>(.*?)</h[1-4]>', re.DOTALL | re.IGNORECASE
)


def looks_like_articles(html: str) -> int:
    """Return count of heading elements that look like article titles."""
    matches = ARTICLE_TITLE_RE.findall(html)
    count = 0
    for m in matches:
        text = re.sub(r'<[^>]+>', '', m).strip()
        # Article titles are typically 15+ chars, not nav items
        if len(text) < 15:
            continue
        skip = ['menu', 'search', 'copyright', 'privacy', 'log in',
                'sign up', 'newsletter', 'widget', 'archives', 'about',
                'contact', 'submit', 'masthead', 'subscribe', 'footer',
                'header', 'sidebar', 'navigation', 'skip to content']
        if any(s in text.lower() for s in skip):
            continue
        count += 1
    return count


def generate_urls(journal_name: str) -> list[tuple[str, str]]:
    """Generate candidate URLs for a journal. Returns (url, description) pairs."""
    urls = []
    name = journal_name.lower()

    # Strip common suffixes/prefixes for slug generation
    # e.g. "Columbia Law Review" -> "columbia-law-review", "columbialawreview"
    slug_dash = re.sub(r'[^a-z0-9]+', '-', name).strip('-')
    slug_no_sep = re.sub(r'[^a-z0-9]', '', name)

    # Extract university name if pattern is "X Law Review" or "X Law Journal"
    uni_match = re.match(r'^(?:university of |u\.?c\.?\s*)?(.+?)(?:\s+law\s+(?:review|journal)).*$', name, re.I)
    uni_slug = None
    if uni_match:
        uni_slug = re.sub(r'[^a-z0-9]+', '', uni_match.group(1).lower())

    # Common patterns
    urls.append((f"https://{slug_dash}.org/", "slug.org"))
    urls.append((f"https://www.{slug_dash}.org/", "www.slug.org"))
    urls.append((f"https://{slug_dash}.org/issues/", "slug.org/issues"))
    urls.append((f"https://{slug_dash}.org/archives/", "slug.org/archives"))
    urls.append((f"https://{slug_dash}.com/", "slug.com"))

    if uni_slug:
        urls.append((f"https://{uni_slug}lawreview.org/", "unilawreview.org"))
        urls.append((f"https://www.{uni_slug}lawreview.org/", "www.unilawreview.org"))
        urls.append((f"https://{uni_slug}lawreview.org/issues/", "unilawreview.org/issues"))
        urls.append((f"https://{uni_slug}lawreview.org/archives/", "unilawreview.org/archives"))

    # Specific well-known patterns for major journals
    known_guesses = {
        "columbia law review": [
            ("https://columbialawreview.org/", "known"),
            ("https://columbialawreview.org/content/", "known"),
        ],
        "harvard law review": [
            ("https://harvardlawreview.org/", "known"),
            ("https://harvardlawreview.org/archive/", "known"),
        ],
        "stanford law review": [
            ("https://www.stanfordlawreview.org/", "known"),
            ("https://www.stanfordlawreview.org/print/", "known"),
        ],
        "yale law journal": [
            ("https://www.yalelawjournal.org/", "known"),
            ("https://www.yalelawjournal.org/issue", "known"),
        ],
        "california law review": [
            ("https://www.californialawreview.org/", "known"),
            ("https://californialawreview.org/", "known"),
        ],
        "university of pennsylvania law review": [
            ("https://www.pennlawreview.com/", "known"),
            ("https://scholarship.law.upenn.edu/penn_law_review/", "known"),
        ],
        "cornell law review": [
            ("https://cornelllawreview.org/", "known"),
            ("https://www.cornelllawreview.org/", "known"),
        ],
        "michigan law review": [
            ("https://michiganlawreview.org/", "known"),
            ("https://www.michiganlawreview.org/", "known"),
        ],
        "university of chicago law review": [
            ("https://lawreview.uchicago.edu/", "known"),
            ("https://chicagounbound.uchicago.edu/uclrev/", "known"),
        ],
        "virginia law review": [
            ("https://www.virginialawreview.org/", "known"),
            ("https://virginialawreview.org/", "known"),
        ],
        "duke law journal": [
            ("https://dlj.law.duke.edu/", "known"),
            ("https://scholarship.law.duke.edu/dlj/", "known"),
        ],
        "new york university law review": [
            ("https://www.nyulawreview.org/", "known"),
            ("https://nyulawreview.org/", "known"),
        ],
        "vanderbilt law review": [
            ("https://vanderbiltlawreview.org/", "known"),
            ("https://www.vanderbiltlawreview.org/", "known"),
        ],
        "minnesota law review": [
            ("https://minnesotalawreview.org/", "known"),
            ("https://www.minnesotalawreview.org/", "known"),
        ],
        "georgetown law journal": [
            ("https://www.law.georgetown.edu/georgetown-law-journal/", "known"),
            ("https://georgetownlawjournal.org/", "known"),
        ],
        "northwestern university law review": [
            ("https://northwesternlawreview.org/", "known"),
            ("https://www.northwesternlawreview.org/", "known"),
            ("https://scholarlycommons.law.northwestern.edu/nulr/", "known"),
        ],
        "texas law review": [
            ("https://texaslawreview.org/", "known"),
            ("https://www.texaslawreview.org/", "known"),
        ],
        "ucla law review": [
            ("https://www.uclalawreview.org/", "known"),
        ],
        "boston college law review": [
            ("https://bclawreview.org/", "known"),
            ("https://www.bc.edu/content/bc-web/schools/law/academics-faculty/journals/bc-law-review.html", "known"),
        ],
        "uc davis law review": [
            ("https://lawreview.law.ucdavis.edu/", "known"),
        ],
        "washington university law review": [
            ("https://wustllawreview.org/", "known"),
            ("https://openscholarship.wustl.edu/law_lawreview/", "known"),
        ],
        "notre dame law review": [
            ("https://ndlawreview.org/", "known"),
            ("https://scholarship.law.nd.edu/ndlr/", "known"),
        ],
        "indiana law journal": [
            ("https://www.repository.law.indiana.edu/ilj/", "known"),
        ],
        "yale journal on regulation": [
            ("https://www.yalejreg.com/", "known"),
        ],
        "southern california law review": [
            ("https://southerncalifornialawreview.com/", "known"),
            ("https://gould.usc.edu/students/journals/lawreview/", "known"),
        ],
        "george washington law review": [
            ("https://www.gwlr.org/", "known"),
        ],
        "university of illinois law review": [
            ("https://illinoislawreview.org/", "known"),
        ],
        "florida law review": [
            ("https://floridalawreview.com/", "known"),
        ],
        "washington law review": [
            ("https://www.washingtonlawreview.org/", "known"),
        ],
        "wisconsin law review": [
            ("https://wlr.law.wisc.edu/", "known"),
        ],
        "william & mary law review": [
            ("https://wmlawreview.org/", "known"),
            ("https://scholarship.law.wm.edu/wmlr/", "known"),
        ],
        "north carolina law review": [
            ("https://nclawreview.org/", "known"),
            ("https://scholarship.law.unc.edu/nclr/", "known"),
        ],
        "cardozo law review": [
            ("https://cardozolawreview.com/", "known"),
        ],
        "ohio state law journal": [
            ("https://moritzlaw.osu.edu/ohio-state-law-journal", "known"),
        ],
        "emory law journal": [
            ("https://scholarlycommons.law.emory.edu/elj/", "known"),
            ("https://law.emory.edu/elj/", "known"),
        ],
        "georgia law review": [
            ("https://georgialawreview.org/", "known"),
        ],
        "journal of criminal law and criminology": [
            ("https://scholarlycommons.law.northwestern.edu/jclc/", "known"),
        ],
        "alabama law review": [
            ("https://www.law.ua.edu/lawreview/", "known"),
        ],
        "harvard journal of law & technology": [
            ("https://jolt.law.harvard.edu/", "known"),
        ],
        "administrative law review": [
            ("https://www.administrativelawreview.org/", "known"),
        ],
        "arizona law review": [
            ("https://arizonalawreview.org/", "known"),
        ],
        "harvard journal of law & public policy": [
            ("https://www.jlpp.org/", "known"),
        ],
    }

    if name in known_guesses:
        for url, desc in known_guesses[name]:
            urls.insert(0, (url, desc))

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for url, desc in urls:
        if url not in seen:
            seen.add(url)
            deduped.append((url, desc))

    return deduped


def main():
    print("Discovering journal websites for top 50 journals...\n")

    with get_session() as session:
        journals = (
            session.query(Journal)
            .filter(Journal.rank.isnot(None))
            .order_by(Journal.rank)
            .limit(50)
            .all()
        )

        # Already known
        already_known = {
            "Fordham Law Review",
            "Boston University Law Review",
            "Iowa Law Review",
        }

        results = []

        for j in journals:
            if j.name in already_known:
                print(f"[SKIP] #{j.rank} {j.name} — already configured")
                continue

            # Skip online forum variants
            if "[online]" in j.name.lower():
                print(f"[SKIP] #{j.rank} {j.name} — online forum, skip")
                continue

            candidate_urls = generate_urls(j.name)
            found = False

            for url, desc in candidate_urls:
                try:
                    resp = httpx.get(
                        url, headers=HEADERS, timeout=12,
                        follow_redirects=True
                    )
                    if resp.status_code == 200:
                        n_articles = looks_like_articles(resp.text)
                        final_url = str(resp.url)
                        if n_articles >= 3:
                            print(f"[OK]   #{j.rank} {j.name}")
                            print(f"       URL: {url} -> {final_url}")
                            print(f"       {n_articles} article-like titles found")
                            results.append({
                                "rank": j.rank,
                                "name": j.name,
                                "url": url,
                                "final_url": final_url,
                                "titles": n_articles,
                            })
                            found = True
                            break
                        # If we got 200 but few titles, try next URL
                    elif resp.status_code == 403:
                        pass  # Cloudflare, skip silently
                except httpx.ConnectError:
                    pass
                except httpx.TimeoutException:
                    pass
                except Exception:
                    pass

                time.sleep(1)  # Be polite between attempts

            if not found:
                print(f"[MISS] #{j.rank} {j.name}")

            time.sleep(1)  # Extra pause between journals

        print(f"\n\nSUMMARY: {len(results)} new sites discovered\n")
        print("Suggested SiteConfig entries:\n")
        for r in results:
            print(f'    SiteConfig(')
            print(f'        journal_name="{r["name"]}",')
            print(f'        archive_url="{r["url"]}",')
            print(f'    ),')
            print()


if __name__ == "__main__":
    main()
