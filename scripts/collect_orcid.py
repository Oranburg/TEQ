"""Collect author metadata from the ORCID public API.

Usage:
    python scripts/collect_orcid.py --author "Seth Oranburg"
    python scripts/collect_orcid.py --orcid "0000-0002-1234-5678"
    python scripts/collect_orcid.py --enrich    # enrich all authors missing ORCID data

ORCID public API is free and requires no authentication.
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
from teq.models import AuditLog, Author

BASE_URL = "https://pub.orcid.org/v3.0"
HEADERS = {"Accept": "application/json"}


def search_orcid(family_name: str, given_names: str | None = None) -> list[dict]:
    """Search ORCID for authors matching a name.

    Returns a list of dicts with orcid_id and basic info for each match.
    """
    query = f"family-name:{family_name}"
    if given_names:
        query += f"+AND+given-names:{given_names}"

    url = f"{BASE_URL}/search/"
    params = {"q": query}

    resp = httpx.get(url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("result", []) or []:
        orcid_id = item.get("orcid-identifier", {}).get("path")
        if orcid_id:
            results.append({"orcid_id": orcid_id})

    return results


def fetch_orcid_record(orcid_id: str) -> dict | None:
    """Fetch a full ORCID record and extract relevant fields.

    Returns a dict with name, orcid, affiliation, employment history,
    and work titles, or None on failure.
    """
    url = f"{BASE_URL}/{orcid_id}/record"
    resp = httpx.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        print(f"  ORCID {orcid_id} not found.")
        return None
    resp.raise_for_status()
    data = resp.json()

    # Extract name
    person = data.get("person", {})
    name_data = person.get("name", {}) or {}
    given = (name_data.get("given-names") or {}).get("value", "")
    family = (name_data.get("family-name") or {}).get("value", "")
    full_name = f"{given} {family}".strip()

    # Extract employment / affiliations
    activities = data.get("activities-summary", {})
    employments_group = (
        activities.get("employments", {}).get("affiliation-group", []) or []
    )
    employment_history = []
    current_affiliation = None
    for group in employments_group:
        summaries = group.get("summaries", [])
        for s in summaries:
            emp = s.get("employment-summary", {})
            org = emp.get("organization", {})
            org_name = org.get("name", "")
            role = emp.get("role-title", "")
            start = emp.get("start-date")
            end = emp.get("end-date")

            entry = {
                "organization": org_name,
                "role": role,
                "start": _format_date(start),
                "end": _format_date(end),
            }
            employment_history.append(entry)

            # Current affiliation: no end date
            if end is None or (end.get("year") is None if isinstance(end, dict) else True):
                if current_affiliation is None:
                    current_affiliation = org_name

    # Extract works (publication titles)
    works_group = activities.get("works", {}).get("group", []) or []
    work_titles = []
    for group in works_group:
        summaries = group.get("work-summary", [])
        if summaries:
            title_data = summaries[0].get("title", {})
            title_val = (title_data.get("title") or {}).get("value")
            if title_val:
                work_titles.append(title_val)

    return {
        "name": full_name,
        "given_name": given,
        "family_name": family,
        "orcid": orcid_id,
        "affiliation": current_affiliation,
        "employment_history": employment_history,
        "works": work_titles,
    }


def _format_date(date_obj: dict | None) -> str | None:
    """Format an ORCID date dict to a string like '2020-01'."""
    if not date_obj or not isinstance(date_obj, dict):
        return None
    year = (date_obj.get("year") or {}).get("value")
    month = (date_obj.get("month") or {}).get("value")
    if not year:
        return None
    if month:
        return f"{year}-{month}"
    return str(year)


def upsert_author(record: dict, session) -> Author:
    """Create or update an Author record from ORCID data."""
    author = session.query(Author).filter_by(orcid=record["orcid"]).first()
    if author is None:
        # Try matching by name if no ORCID match
        author = (
            session.query(Author)
            .filter_by(family_name=record["family_name"])
            .filter_by(given_name=record["given_name"])
            .first()
        )

    if author is None:
        author = Author(
            name=record["name"],
            family_name=record["family_name"],
            given_name=record["given_name"],
            orcid=record["orcid"],
            affiliation=record.get("affiliation"),
        )
        session.add(author)
        print(f"  Created author: {record['name']} ({record['orcid']})")
    else:
        author.orcid = record["orcid"]
        author.name = record["name"]
        author.family_name = record["family_name"]
        author.given_name = record["given_name"]
        if record.get("affiliation"):
            author.affiliation = record["affiliation"]
        print(f"  Updated author: {record['name']} ({record['orcid']})")

    return author


def collect_by_name(name: str) -> None:
    """Search ORCID by author name, fetch records, and store."""
    parts = name.strip().rsplit(" ", 1)
    if len(parts) == 2:
        given_names, family_name = parts
    else:
        family_name = parts[0]
        given_names = None

    print(f"Searching ORCID for: {name}")
    print(f"  family-name={family_name}, given-names={given_names}")

    matches = search_orcid(family_name, given_names)
    print(f"  Found {len(matches)} ORCID match(es).")

    if not matches:
        return

    init_db()
    with get_session() as session:
        stored = 0
        for match in matches[:10]:  # cap at 10 to avoid flooding
            orcid_id = match["orcid_id"]
            record = fetch_orcid_record(orcid_id)
            if record is None:
                continue

            author = upsert_author(record, session)
            stored += 1

            # Audit log
            log = AuditLog(
                action="orcid_collection",
                entity_type="Author",
                entity_id=author.id,
                details=json.dumps({
                    "orcid": record["orcid"],
                    "name": record["name"],
                    "affiliation": record.get("affiliation"),
                    "works_count": len(record.get("works", [])),
                    "source": "orcid_search",
                    "query": name,
                }),
            )
            session.add(log)

            time.sleep(0.5)  # rate limit

        print(f"  Stored/updated {stored} author(s).")


def collect_by_orcid(orcid_id: str) -> None:
    """Fetch a single ORCID record by ID and store."""
    print(f"Fetching ORCID record: {orcid_id}")

    record = fetch_orcid_record(orcid_id)
    if record is None:
        print("  No record found.")
        return

    print(f"  Name: {record['name']}")
    print(f"  Affiliation: {record.get('affiliation', 'N/A')}")
    print(f"  Works: {len(record.get('works', []))}")

    init_db()
    with get_session() as session:
        author = upsert_author(record, session)

        log = AuditLog(
            action="orcid_collection",
            entity_type="Author",
            entity_id=author.id,
            details=json.dumps({
                "orcid": record["orcid"],
                "name": record["name"],
                "affiliation": record.get("affiliation"),
                "works_count": len(record.get("works", [])),
                "source": "orcid_direct",
            }),
        )
        session.add(log)

    print("  Done.")


def enrich_all() -> None:
    """Enrich all Author records in the DB that lack ORCID data."""
    init_db()

    with get_session() as session:
        authors = (
            session.query(Author)
            .filter(Author.orcid.is_(None))
            .filter(Author.family_name.isnot(None))
            .all()
        )

        if not authors:
            print("No authors without ORCID data found.")
            return

        print(f"Enriching {len(authors)} author(s) without ORCID data...")

        enriched = 0
        for author in authors:
            print(f"\n  Searching for: {author.name}")
            matches = search_orcid(author.family_name, author.given_name)

            if not matches:
                print(f"    No ORCID matches for {author.name}")
                continue

            # Take the first match only for enrichment
            record = fetch_orcid_record(matches[0]["orcid_id"])
            if record is None:
                continue

            # Verify name similarity before updating
            if record["family_name"].lower() != author.family_name.lower():
                print(f"    Skipping: family name mismatch ({record['family_name']} vs {author.family_name})")
                continue

            author.orcid = record["orcid"]
            if record.get("affiliation"):
                author.affiliation = record["affiliation"]
            enriched += 1

            log = AuditLog(
                action="orcid_enrichment",
                entity_type="Author",
                entity_id=author.id,
                details=json.dumps({
                    "orcid": record["orcid"],
                    "name": record["name"],
                    "affiliation": record.get("affiliation"),
                    "works_count": len(record.get("works", [])),
                    "source": "orcid_enrich",
                }),
            )
            session.add(log)

            time.sleep(0.5)  # rate limit

        print(f"\nEnriched {enriched} of {len(authors)} author(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect author data from ORCID public API."
    )
    parser.add_argument(
        "--author", type=str, default=None,
        help='Search by author name, e.g. --author "Seth Oranburg"',
    )
    parser.add_argument(
        "--orcid", type=str, default=None,
        help='Fetch by ORCID ID, e.g. --orcid "0000-0002-1234-5678"',
    )
    parser.add_argument(
        "--enrich", action="store_true",
        help="Enrich all authors in DB that lack ORCID data",
    )
    args = parser.parse_args()

    if not any([args.author, args.orcid, args.enrich]):
        parser.print_help()
        sys.exit(1)

    if args.author:
        collect_by_name(args.author)
    elif args.orcid:
        collect_by_orcid(args.orcid)
    elif args.enrich:
        enrich_all()


if __name__ == "__main__":
    main()
