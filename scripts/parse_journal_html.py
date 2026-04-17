"""Parse saved law review HTML pages into the TEQ database.

Handles HTML files saved from journal websites via Cmd+S.
Currently supports: Columbia Law Review (WordPress theme).

Usage:
    python scripts/parse_journal_html.py ~/Downloads/Content*.html
    python scripts/parse_journal_html.py --dir ~/Downloads/ --pattern "*Columbia*"

The parser extracts: title, authors, topic, volume, issue, abstract.
It also infers piece_type (article, note, comment, book review, essay)
from structural cues in the HTML and title patterns.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teq.database import get_session, init_db
from teq.models import Article, AuditLog, Journal


def clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def infer_piece_type(title: str, topic: str, authors: str, context: str) -> str:
    """Infer the type of piece from available signals.

    Returns one of: article, note, comment, essay, book_review,
    symposium, response, foreword, tribute, editorial, unknown.

    This is a heuristic classifier. It will be wrong sometimes.
    Manual audit on a 10% sample is required before analysis.
    """
    title_lower = title.lower()
    context_lower = context.lower()

    # Book reviews
    if "book review" in context_lower or "book review" in title_lower:
        return "book_review"
    if title_lower.startswith("review of ") or title_lower.startswith("reviewing "):
        return "book_review"

    # Notes (student-written)
    if "note" in context_lower.split() or "notes" in context_lower.split():
        return "note"

    # Comments (student-written)
    if "comment" in context_lower.split() or "comments" in context_lower.split():
        return "comment"

    # Essays
    if "essay" in context_lower.split() or "essays" in context_lower.split():
        return "essay"

    # Responses/replies
    if any(w in title_lower for w in ["response to", "reply to", "a rejoinder"]):
        return "response"

    # Forewords
    if title_lower.startswith("foreword"):
        return "foreword"

    # Tributes/memorials
    if any(w in title_lower for w in ["tribute to", "in memoriam", "in memory of"]):
        return "tribute"

    # Symposium pieces
    if "symposium" in context_lower or "symposium" in title_lower:
        return "symposium"

    # Author signals for student vs. faculty
    # Students typically have * (single asterisk) for J.D. candidate
    # Faculty have ** or named chair positions
    # This is very rough
    if authors:
        if re.search(r"\*\*", authors):
            return "article"  # likely faculty (double asterisk = endowed position)

    # Default: if it's in a flagship and none of the above matched, it's probably an article
    return "article"


def infer_author_type(authors: str) -> str:
    """Guess whether authors are faculty, student, practitioner, or judge.

    Returns: faculty, student, practitioner, judge, mixed, unknown.
    Heuristic only. Requires manual validation.
    """
    if not authors:
        return "unknown"

    authors_lower = authors.lower()

    # Judge signals
    if any(w in authors_lower for w in ["judge", "justice", "hon."]):
        return "judge"

    # Student signals (typically single * with J.D. candidate)
    # This is unreliable without the footnote text
    if re.search(r"(?<!\*)\*(?!\*)", authors) and "**" not in authors:
        # Single asterisk only, might be student
        pass  # Can't be sure

    # Practitioner signals
    if any(w in authors_lower for w in ["partner", "associate", "counsel", "esq"]):
        return "practitioner"

    # Default to unknown; manual classification needed
    return "unknown"


def parse_columbia_html(html: str) -> list[dict]:
    """Parse Columbia Law Review HTML into article dicts."""
    articles = []

    # Find all article blocks (div with class content-NNNN loop-item)
    blocks = re.findall(
        r'class="content-\d+ loop-item"(.*?)(?=class="content-\d+ loop-item"|</main|</body|$)',
        html,
        re.DOTALL,
    )

    for block in blocks:
        # Topic tag
        topic_matches = re.findall(r'class="topic[^"]*"[^>]*>([^<]+)', block)
        topic = topic_matches[0].strip() if topic_matches else ""

        # Issue reference
        issue_matches = re.findall(r'class="category issue"[^>]*>([^<]+)', block)
        issue_str = issue_matches[0].strip() if issue_matches else ""

        # Parse volume and issue number
        vol_match = re.search(r"Vol\.\s*(\d+)", issue_str)
        issue_match = re.search(r"No\.\s*(\d+)", issue_str)
        volume = vol_match.group(1) if vol_match else None
        issue_num = issue_match.group(1) if issue_match else None

        # Title (h2)
        title_matches = re.findall(r"<h2[^>]*>(.*?)</h2>", block, re.DOTALL)
        if not title_matches:
            continue
        title = clean_html(title_matches[0])
        if len(title) < 5:
            continue

        # Author
        author_matches = re.findall(
            r'class="author"[^>]*>(.*?)</(?:span|div|p)', block, re.DOTALL
        )
        authors = clean_html(author_matches[0]) if author_matches else None

        # Abstract/introduction text
        intro_matches = re.findall(
            r'class="sh-content-wrap"[^>]*>(.*?)</div>', block, re.DOTALL
        )
        abstract = clean_html(intro_matches[0])[:500] if intro_matches else None

        # Infer piece type and author type
        piece_type = infer_piece_type(title, topic, authors or "", block)
        author_type = infer_author_type(authors or "")

        articles.append({
            "title": title,
            "authors": authors,
            "volume": volume,
            "issue": issue_num,
            "topic": topic,
            "abstract": abstract,
            "piece_type": piece_type,
            "author_type": author_type,
            "source": "journal_website",
        })

    return articles


def detect_journal(html: str, filename: str) -> str | None:
    """Detect which journal this HTML is from."""
    if "columbia" in filename.lower() or "columbia law review" in html.lower()[:5000]:
        return "Columbia Law Review"
    # Add more journal detectors as needed
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse saved journal HTML pages into TEQ database."
    )
    parser.add_argument("files", nargs="*", help="HTML files to parse")
    parser.add_argument("--dir", type=str, help="Directory to search")
    parser.add_argument(
        "--pattern", type=str, default="*.html", help="Glob pattern (default: *.html)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print without storing to database",
    )
    args = parser.parse_args()

    # Collect file paths
    paths = []
    if args.files:
        paths = [Path(f) for f in args.files]
    elif args.dir:
        paths = sorted(Path(args.dir).glob(args.pattern))
    else:
        parser.print_help()
        return

    if not paths:
        print("No files found.")
        return

    init_db()
    total_stored = 0
    total_parsed = 0

    with get_session() as session:
        for path in paths:
            if not path.exists():
                print(f"  SKIP: {path} not found")
                continue

            html = path.read_text(encoding="utf-8", errors="replace")
            journal_name = detect_journal(html, path.name)

            if not journal_name:
                print(f"  SKIP: {path.name} (can't detect journal)")
                continue

            # Find journal in DB
            journal = (
                session.query(Journal)
                .filter(Journal.name.ilike(f"%{journal_name}%"))
                .first()
            )
            if not journal:
                print(f"  SKIP: {journal_name} not in database")
                continue

            # Parse based on detected journal
            if "columbia" in journal_name.lower():
                articles = parse_columbia_html(html)
            else:
                print(f"  SKIP: no parser for {journal_name}")
                continue

            total_parsed += len(articles)
            print(f"\n  {path.name} ({journal_name}): {len(articles)} pieces found")

            stored = 0
            for art in articles:
                if args.dry_run:
                    marker = f"[{art['piece_type']}]"
                    print(f"    {marker:15s} {art['title'][:60]}")
                    if art["authors"]:
                        print(f"    {'':15s} by {art['authors'][:60]}")
                    continue

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
                    volume=art["volume"],
                    authors=art["authors"],
                    source=art["source"],
                )
                session.add(article)
                stored += 1

            total_stored += stored
            if not args.dry_run:
                print(f"    Stored {stored} new, skipped {len(articles) - stored} dupes")

        if not args.dry_run:
            log = AuditLog(
                action="html_parse",
                entity_type="Article",
                details=json.dumps({
                    "files": [str(p) for p in paths],
                    "parsed": total_parsed,
                    "stored": total_stored,
                }),
            )
            session.add(log)

    print(f"\nTotal: parsed {total_parsed}, stored {total_stored}")


if __name__ == "__main__":
    main()
