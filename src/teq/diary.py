"""Research diary utilities for TEQ."""

from __future__ import annotations

import re
from pathlib import Path

# Directory where diary entries are stored, relative to the repository root.
_DIARY_DIR = Path(__file__).resolve().parents[2] / "research"


def _slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text


def _next_entry_number() -> int:
    """Return the next sequential entry number based on existing files."""
    existing = list(_DIARY_DIR.glob("[0-9][0-9][0-9]_*.md"))
    if not existing:
        return 1
    numbers = []
    for path in existing:
        match = re.match(r"^(\d{3})_", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers) + 1 if numbers else 1


def create_entry(title: str, content: str) -> str:
    """Create a new research diary entry as a markdown file in research/.

    Filename format: NNN_slugified-title.md
    Returns the file path.
    """
    _DIARY_DIR.mkdir(parents=True, exist_ok=True)
    number = _next_entry_number()
    slug = _slugify(title)
    filename = f"{number:03d}_{slug}.md"
    path = _DIARY_DIR / filename
    path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
    return str(path)


def list_entries() -> list[str]:
    """List all diary entries by filename."""
    if not _DIARY_DIR.exists():
        return []
    entries = sorted(
        path.name for path in _DIARY_DIR.glob("[0-9][0-9][0-9]_*.md")
    )
    return entries
