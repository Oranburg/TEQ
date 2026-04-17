"""CLI script to run feature extraction on articles in the TEQ database.

Usage:
    python scripts/extract_features.py [--limit N]

Reads Article records from the database, extracts title features, and stores
TitleFeature records. Skips articles that already have features at the current
FEATURE_VERSION.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teq.database import get_session, init_db
from teq.features import FEATURE_VERSION, extract_features
from teq.models import Article, TitleFeature


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract title features for all articles in the TEQ database."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to process (default: all).",
    )
    args = parser.parse_args()

    init_db()

    processed = 0
    skipped = 0

    with get_session() as session:
        query = session.query(Article)
        if args.limit is not None:
            query = query.limit(args.limit)
        articles = query.all()

        for article in articles:
            # Check if features already exist for this version.
            existing = (
                session.query(TitleFeature)
                .filter_by(
                    article_id=article.id,
                    extraction_version=FEATURE_VERSION,
                )
                .first()
            )
            if existing is not None:
                skipped += 1
                continue

            features = extract_features(article.title)
            for name, value in features.items():
                tf = TitleFeature(
                    article_id=article.id,
                    feature_name=name,
                    feature_value=value,
                    extraction_version=FEATURE_VERSION,
                )
                session.add(tf)
            processed += 1

    print(f"Feature extraction complete.")
    print(f"  Articles processed: {processed}")
    print(f"  Articles skipped (already extracted): {skipped}")
    print(f"  Feature version: {FEATURE_VERSION}")


if __name__ == "__main__":
    main()
