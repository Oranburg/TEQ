"""Feature extraction module for TEQ.

All features are deterministic: the same title always produces the same output.
Features return float values. Stub features return 0.0 pending implementation.
"""

from __future__ import annotations

FEATURE_VERSION = "0.1.0"

# Words excluded from title-case ratio calculation.
_STOP_WORDS = {
    "a", "an", "the", "and", "but", "or", "for", "nor", "on", "at",
    "to", "by", "in", "of", "up", "as", "is", "it", "its",
}


def extract_features(title: str) -> dict[str, float]:
    """Extract measurable features from an article title.

    Returns a dict mapping feature names to numeric values.
    All features must be deterministic — same input always produces same output.
    """
    return {
        # Implemented features
        "word_count": _word_count(title),
        "char_count": _char_count(title),
        "has_colon": _has_colon(title),
        "has_question_mark": _has_question_mark(title),
        "has_subtitle": _has_subtitle(title),
        "title_case_ratio": _title_case_ratio(title),
        # Stub features
        "flesch_reading_ease": _flesch_reading_ease(title),
        "avg_word_length": _avg_word_length(title),
        "jargon_density": _jargon_density(title),
        "novelty_score": _novelty_score(title),
        "abstractness_score": _abstractness_score(title),
        "named_entity_count": _named_entity_count(title),
        "sentiment_polarity": _sentiment_polarity(title),
        "punctuation_density": _punctuation_density(title),
    }


# ---------------------------------------------------------------------------
# Implemented features
# ---------------------------------------------------------------------------


def _word_count(title: str) -> float:
    """Number of whitespace-delimited tokens."""
    return float(len(title.split()))


def _char_count(title: str) -> float:
    """Total number of characters in the title."""
    return float(len(title))


def _has_colon(title: str) -> float:
    """1.0 if the title contains a colon, else 0.0."""
    return 1.0 if ":" in title else 0.0


def _has_question_mark(title: str) -> float:
    """1.0 if the title contains a question mark, else 0.0."""
    return 1.0 if "?" in title else 0.0


def _has_subtitle(title: str) -> float:
    """1.0 if the title contains ':' or '—' (em-dash), else 0.0."""
    return 1.0 if (":" in title or "\u2014" in title) else 0.0


def _title_case_ratio(title: str) -> float:
    """Fraction of words that are title-cased, excluding common stop words."""
    words = title.split()
    content_words = [w for w in words if w.lower().strip(".,;:!?\"'") not in _STOP_WORDS]
    if not content_words:
        return 0.0
    title_cased = sum(1 for w in content_words if w and w[0].isupper())
    return title_cased / len(content_words)


# ---------------------------------------------------------------------------
# Stub features — not yet implemented
# ---------------------------------------------------------------------------


def _flesch_reading_ease(title: str) -> float:  # TODO: implement using syllable count
    return 0.0


def _avg_word_length(title: str) -> float:  # TODO: implement average characters per word
    return 0.0


def _jargon_density(title: str) -> float:  # TODO: implement using legal jargon dictionary
    return 0.0


def _novelty_score(title: str) -> float:  # TODO: implement inverse bigram frequency in corpus
    return 0.0


def _abstractness_score(title: str) -> float:  # TODO: implement abstract/concrete noun ratio
    return 0.0


def _named_entity_count(title: str) -> float:  # TODO: implement using spaCy NER
    return 0.0


def _sentiment_polarity(title: str) -> float:  # TODO: implement using a sentiment lexicon
    return 0.0


def _punctuation_density(title: str) -> float:  # TODO: implement punctuation chars / total chars
    return 0.0


# ---------------------------------------------------------------------------
# Introspection helpers
# ---------------------------------------------------------------------------

_IMPLEMENTED_FEATURES = [
    "word_count",
    "char_count",
    "has_colon",
    "has_question_mark",
    "has_subtitle",
    "title_case_ratio",
]

_STUB_FEATURES = [
    "flesch_reading_ease",
    "avg_word_length",
    "jargon_density",
    "novelty_score",
    "abstractness_score",
    "named_entity_count",
    "sentiment_polarity",
    "punctuation_density",
]


def list_features() -> list[str]:
    """Return names of all implemented features."""
    return list(_IMPLEMENTED_FEATURES)


def list_stub_features() -> list[str]:
    """Return names of features not yet implemented (stub only)."""
    return list(_STUB_FEATURES)
