"""Feature extraction module for TEQ.

All features are deterministic: the same title always produces the same output.
Features return float values. Stub features return 0.0 pending implementation.

Candidate features follow the research design (docs/research-design.md, Section 4).
Features are organized by category:
  4.1  Length
  4.2  Punctuation and Structure
  4.3  Structural Templates
  4.4  Doctrinal and Legal Signals
  4.5  Novelty and Creativity
  4.6  Sentiment and Tone
  4.7  NLP Features
  4.8  Computed Interaction Features
"""

from __future__ import annotations
import math

FEATURE_VERSION = "0.2.0"

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
        # --- 4.1 Length ---
        "char_count": _char_count(title),
        "word_count": _word_count(title),
        "log_char_count": _log_char_count(title),

        # --- 4.2 Punctuation and Structure ---
        "has_colon": _has_colon(title),
        "has_question_mark": _has_question_mark(title),
        "has_em_dash": _has_em_dash(title),
        "has_comma": _has_comma(title),
        "num_punctuation": _num_punctuation(title),
        "subtitle_length_ratio": _subtitle_length_ratio(title),

        # --- 4.3 Structural Templates ---
        "tmpl_the_x_of_y": _tmpl_the_x_of_y(title),
        "tmpl_beyond_x": _tmpl_beyond_x(title),
        "tmpl_rethinking_x": _tmpl_rethinking_x(title),
        "tmpl_x_in_age_of_y": _tmpl_x_in_age_of_y(title),
        "tmpl_toward_x": _tmpl_toward_x(title),
        "tmpl_x_and_y": _tmpl_x_and_y(title),
        "tmpl_against_x": _tmpl_against_x(title),
        "tmpl_defense_of_x": _tmpl_defense_of_x(title),
        "tmpl_death_of_x": _tmpl_death_of_x(title),

        # --- 4.4 Doctrinal and Legal Signals ---
        "has_case_name": _has_case_name(title),
        "has_statute_ref": _has_statute_ref(title),
        "has_amendment_ref": _has_amendment_ref(title),
        "has_jurisdiction": _has_jurisdiction(title),
        "num_legal_terms": _num_legal_terms(title),
        "legal_term_density": _legal_term_density(title),

        # --- 4.5 Novelty and Creativity ---
        "has_neologism": _has_neologism(title),
        "has_pop_culture": _has_pop_culture(title),
        "has_metaphor_signal": _has_metaphor_signal(title),
        "title_novelty_score": _title_novelty_score(title),
        "has_alliteration": _has_alliteration(title),

        # --- 4.6 Sentiment and Tone ---
        "sentiment_polarity": _sentiment_polarity(title),
        "sentiment_subjectivity": _sentiment_subjectivity(title),
        "is_provocative": _is_provocative(title),
        "has_normative_verb": _has_normative_verb(title),

        # --- 4.7 NLP Features ---
        "noun_ratio": _noun_ratio(title),
        "adj_ratio": _adj_ratio(title),
        "verb_ratio": _verb_ratio(title),
        "named_entity_count": _named_entity_count(title),
        "named_entity_density": _named_entity_density(title),
        "semantic_similarity_to_journal": _semantic_similarity_to_journal(title),
        "abstractness_score": _abstractness_score(title),

        # --- 4.8 Computed Interaction Features ---
        "length_x_colon": _length_x_colon(title),
        "novelty_x_specialty": _novelty_x_specialty(title),
        "legal_density_x_rank": _legal_density_x_rank(title),

        # --- Legacy / auxiliary features (not in Section 4 candidate list) ---
        "has_subtitle": _has_subtitle(title),
        "title_case_ratio": _title_case_ratio(title),
        "avg_word_length": _avg_word_length(title),
        "flesch_reading_ease": _flesch_reading_ease(title),
        "punctuation_density": _punctuation_density(title),
    }


# ---------------------------------------------------------------------------
# 4.1 Length Features
# ---------------------------------------------------------------------------


def _char_count(title: str) -> float:
    """Total number of characters in the title, including spaces."""
    return float(len(title))


def _word_count(title: str) -> float:
    """Number of whitespace-delimited tokens."""
    return float(len(title.split()))


def _log_char_count(title: str) -> float:
    """Natural log of char_count. Tests the diminishing-returns hypothesis."""
    c = len(title)
    return math.log(c) if c > 0 else 0.0


# ---------------------------------------------------------------------------
# 4.2 Punctuation and Structure
# ---------------------------------------------------------------------------


def _has_colon(title: str) -> float:
    """1.0 if the title contains a colon, else 0.0."""
    return 1.0 if ":" in title else 0.0


def _has_question_mark(title: str) -> float:
    """1.0 if the title contains a question mark, else 0.0."""
    return 1.0 if "?" in title else 0.0


def _has_em_dash(title: str) -> float:
    """1.0 if the title contains an em-dash (—) or en-dash (–), else 0.0."""
    return 1.0 if ("\u2014" in title or "\u2013" in title) else 0.0


def _has_comma(title: str) -> float:
    """1.0 if the title contains a comma, else 0.0."""
    return 1.0 if "," in title else 0.0


def _num_punctuation(title: str) -> float:
    """Count of all punctuation characters in the title."""
    punct = set('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~\u2014\u2013')
    return float(sum(1 for ch in title if ch in punct))


def _subtitle_length_ratio(title: str) -> float:
    """Words after colon / total words, if a colon is present; else 0.0."""
    if ":" not in title:
        return 0.0
    parts = title.split(":", 1)
    total = len(title.split())
    if total == 0:
        return 0.0
    after = len(parts[1].split())
    return after / total


# ---------------------------------------------------------------------------
# 4.3 Structural Templates (binary regex flags)
# ---------------------------------------------------------------------------


import re as _re


def _tmpl_the_x_of_y(title: str) -> float:
    """1.0 if title matches ^The \\w+ of (e.g. 'The Limits of Contract')."""
    return 1.0 if _re.match(r"^The\s+\w+\s+of\b", title, _re.IGNORECASE) else 0.0


def _tmpl_beyond_x(title: str) -> float:
    """1.0 if title starts with 'Beyond'."""
    return 1.0 if _re.match(r"^Beyond\b", title, _re.IGNORECASE) else 0.0


def _tmpl_rethinking_x(title: str) -> float:
    """1.0 if title starts with Rethinking, Reconsidering, Reimagining, or Reexamining."""
    pattern = r"^(Rethinking|Reconsidering|Reimagining|Reexamining)\b"
    return 1.0 if _re.match(pattern, title, _re.IGNORECASE) else 0.0


def _tmpl_x_in_age_of_y(title: str) -> float:
    """1.0 if title contains 'in the (Age|Era|Time|Wake) of'."""
    pattern = r"\bin\s+the\s+(Age|Era|Time|Wake)\s+of\b"
    return 1.0 if _re.search(pattern, title, _re.IGNORECASE) else 0.0


def _tmpl_toward_x(title: str) -> float:
    """1.0 if title starts with 'Toward' or 'Towards'."""
    return 1.0 if _re.match(r"^Towards?\b", title, _re.IGNORECASE) else 0.0


def _tmpl_x_and_y(title: str) -> float:
    """1.0 if the title is exactly two alphabetic words joined by 'and' (e.g. 'Property and Personhood')."""
    return 1.0 if _re.match(r"^[A-Za-z]+\s+and\s+[A-Za-z]+$", title, _re.IGNORECASE) else 0.0


def _tmpl_against_x(title: str) -> float:
    """1.0 if title starts with 'Against'."""
    return 1.0 if _re.match(r"^Against\b", title, _re.IGNORECASE) else 0.0


def _tmpl_defense_of_x(title: str) -> float:
    """1.0 if title contains 'In Defense of' or starts with 'Defending'."""
    pattern = r"(In\s+Defense\s+of\b|^Defending\b)"
    return 1.0 if _re.search(pattern, title, _re.IGNORECASE) else 0.0


def _tmpl_death_of_x(title: str) -> float:
    """1.0 if title contains 'Death of', 'End of', or 'Demise of'."""
    pattern = r"\b(Death|End|Demise)\s+of\b"
    return 1.0 if _re.search(pattern, title, _re.IGNORECASE) else 0.0


# ---------------------------------------------------------------------------
# 4.4 Doctrinal and Legal Signals
# ---------------------------------------------------------------------------


def _has_case_name(title: str) -> float:
    """1.0 if the title contains a 'Party v. Party' construction with capitalized names, else 0.0."""
    return 1.0 if _re.search(r"\b[A-Z]\w+\s+v\.?\s+[A-Z]\w+\b", title) else 0.0


def _has_statute_ref(title: str) -> float:
    """1.0 if the title references a statute, section symbol, or 'Act', else 0.0."""
    pattern = r"\b(Section|Act|\u00a7|\d+\s+U\.?S\.?C\.?)\b"
    return 1.0 if _re.search(pattern, title, _re.IGNORECASE) else 0.0


def _has_amendment_ref(title: str) -> float:
    """1.0 if the title references a constitutional amendment, else 0.0."""
    # TODO: implement using a full ordinal list; currently covers common amendments
    ordinals = (
        "First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|"
        "Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|"
        "Seventeenth|Eighteenth|Nineteenth|Twentieth|Twenty-First|"
        "Twenty-Second|Twenty-Third|Twenty-Fourth|Twenty-Fifth|"
        "Twenty-Sixth|Twenty-Seventh"
    )
    pattern = rf"\b({ordinals})\s+Amendment\b"
    return 1.0 if _re.search(pattern, title, _re.IGNORECASE) else 0.0


def _has_jurisdiction(title: str) -> float:
    """1.0 if the title names a specific jurisdiction, else 0.0.

    TODO: implement using spaCy NER (GPE entities) or a jurisdiction dictionary.
    """
    return 0.0


def _num_legal_terms(title: str) -> float:
    """Count of legal terms of art found in the title.

    TODO: implement using a ~500-term legal vocabulary dictionary.
    """
    return 0.0


def _legal_term_density(title: str) -> float:
    """num_legal_terms / word_count. Returns 0.0 if title is empty.

    TODO: implement once _num_legal_terms is populated.
    """
    wc = _word_count(title)
    return _num_legal_terms(title) / wc if wc > 0 else 0.0


# ---------------------------------------------------------------------------
# 4.5 Novelty and Creativity
# ---------------------------------------------------------------------------


def _has_neologism(title: str) -> float:
    """1.0 if the title contains a word absent from a standard dictionary, else 0.0.

    TODO: implement using aspell or the nltk words corpus.
    """
    return 0.0


def _has_pop_culture(title: str) -> float:
    """1.0 if the title references a pop culture term or name, else 0.0.

    TODO: implement using a curated pop-culture term dictionary.
    """
    return 0.0


def _has_metaphor_signal(title: str) -> float:
    """1.0 if the title uses metaphorical language markers, else 0.0.

    Markers: figurative verbs such as 'weaponize', 'unlock', 'bridge', 'fuel',
    or simile markers such as 'as a'.
    TODO: implement using a figurative-language verb list and regex.
    """
    return 0.0


def _title_novelty_score(title: str) -> float:
    """TF-IDF cosine distance of the title from the corpus centroid.

    Requires the full article corpus to be loaded; returns 0.0 as a stub.
    TODO: implement post-collection using sklearn TfidfVectorizer.
    """
    return 0.0


def _has_alliteration(title: str) -> float:
    """1.0 if two or more consecutive words share the same first letter, else 0.0."""
    words = [w for w in title.split() if w.isalpha()]
    for i in range(len(words) - 1):
        if words[i][0].lower() == words[i + 1][0].lower():
            return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# 4.6 Sentiment and Tone
# ---------------------------------------------------------------------------


def _sentiment_polarity(title: str) -> float:
    """Continuous [-1, 1]: negative to positive sentiment.

    TODO: implement using VADER or TextBlob.
    """
    return 0.0


def _sentiment_subjectivity(title: str) -> float:
    """Continuous [0, 1]: objective (0) to subjective (1).

    TODO: implement using TextBlob subjectivity.
    """
    return 0.0


def _is_provocative(title: str) -> float:
    """1.0 if the title contains charged/strong language, else 0.0.

    Uses a small seed dictionary; should be expanded before analysis.
    """
    _PROVOCATIVE_TERMS = {
        "myth", "myths", "lie", "lies", "failure", "failures", "broken",
        "crisis", "disaster", "corrupt", "fraud", "scandal", "outrage",
        "wrong", "dead", "kill", "killing", "assault", "attack",
    }
    words = {w.lower().strip(".,;:!?\"'") for w in title.split()}
    return 1.0 if words & _PROVOCATIVE_TERMS else 0.0


def _has_normative_verb(title: str) -> float:
    """1.0 if the title contains 'should', 'must', or 'ought', else 0.0."""
    pattern = r"\b(should|must|ought)\b"
    return 1.0 if _re.search(pattern, title, _re.IGNORECASE) else 0.0


# ---------------------------------------------------------------------------
# 4.7 NLP Features
# ---------------------------------------------------------------------------


def _noun_ratio(title: str) -> float:
    """Proportion of words that are nouns (spaCy POS tagging).

    TODO: implement using spaCy en_core_web_sm or larger model.
    """
    return 0.0


def _adj_ratio(title: str) -> float:
    """Proportion of words that are adjectives (spaCy POS tagging).

    TODO: implement using spaCy.
    """
    return 0.0


def _verb_ratio(title: str) -> float:
    """Proportion of words that are verbs (spaCy POS tagging).

    TODO: implement using spaCy.
    """
    return 0.0


def _named_entity_count(title: str) -> float:
    """Number of named entities (people, orgs, places) detected by spaCy NER.

    TODO: implement using spaCy NER.
    """
    return 0.0


def _named_entity_density(title: str) -> float:
    """named_entity_count / word_count. Returns 0.0 if title is empty."""
    wc = _word_count(title)
    return _named_entity_count(title) / wc if wc > 0 else 0.0


def _semantic_similarity_to_journal(title: str) -> float:
    """Cosine similarity between the title embedding and the journal's typical title embedding.

    Requires journal context and Sentence-BERT embeddings; always 0.0 without corpus.
    TODO: implement using sentence-transformers.
    """
    return 0.0


def _abstractness_score(title: str) -> float:
    """Average word concreteness rating (Brysbaert et al., 2014 norms).

    TODO: implement using the Brysbaert concreteness ratings lookup table.
    """
    return 0.0


# ---------------------------------------------------------------------------
# 4.8 Computed Interaction Features
# ---------------------------------------------------------------------------


def _length_x_colon(title: str) -> float:
    """Interaction: word_count × has_colon."""
    return _word_count(title) * _has_colon(title)


def _novelty_x_specialty(title: str) -> float:
    """Interaction: title_novelty_score × journal specialty status.

    Journal specialty is not available at the title level; returns 0.0 until
    journal context is passed in.
    TODO: refactor to accept journal metadata as an argument.
    """
    return 0.0


def _legal_density_x_rank(title: str) -> float:
    """Interaction: legal_term_density × journal W&L rank.

    Journal rank is not available at the title level; returns 0.0 until
    journal context is passed in.
    TODO: refactor to accept journal metadata as an argument.
    """
    return 0.0


# ---------------------------------------------------------------------------
# Legacy / auxiliary features (not in Section 4 candidate list)
# ---------------------------------------------------------------------------


def _has_subtitle(title: str) -> float:
    """1.0 if the title contains ':' or '—' (em-dash), else 0.0."""
    return 1.0 if (":" in title or "\u2014" in title) else 0.0


def _title_case_ratio(title: str) -> float:
    """Fraction of content words that are title-cased, excluding stop words."""
    words = title.split()
    content_words = [w for w in words if w.lower().strip(".,;:!?\"'") not in _STOP_WORDS]
    if not content_words:
        return 0.0
    title_cased = sum(1 for w in content_words if w and w[0].isupper())
    return title_cased / len(content_words)


def _avg_word_length(title: str) -> float:
    """Average number of characters per word."""
    words = title.split()
    if not words:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def _flesch_reading_ease(title: str) -> float:
    """Flesch Reading Ease score approximation.

    TODO: implement using syllable count (textstat or custom syllable counter).
    """
    return 0.0


def _punctuation_density(title: str) -> float:
    """Punctuation characters / total characters. Returns 0.0 for empty title."""
    if not title:
        return 0.0
    return _num_punctuation(title) / len(title)


# ---------------------------------------------------------------------------
# Introspection helpers
# ---------------------------------------------------------------------------

_SECTION4_FEATURES = [
    # 4.1 Length
    "char_count",
    "word_count",
    "log_char_count",
    # 4.2 Punctuation and Structure
    "has_colon",
    "has_question_mark",
    "has_em_dash",
    "has_comma",
    "num_punctuation",
    "subtitle_length_ratio",
    # 4.3 Structural Templates
    "tmpl_the_x_of_y",
    "tmpl_beyond_x",
    "tmpl_rethinking_x",
    "tmpl_x_in_age_of_y",
    "tmpl_toward_x",
    "tmpl_x_and_y",
    "tmpl_against_x",
    "tmpl_defense_of_x",
    "tmpl_death_of_x",
    # 4.4 Doctrinal and Legal Signals
    "has_case_name",
    "has_statute_ref",
    "has_amendment_ref",
    "has_jurisdiction",
    "num_legal_terms",
    "legal_term_density",
    # 4.5 Novelty and Creativity
    "has_neologism",
    "has_pop_culture",
    "has_metaphor_signal",
    "title_novelty_score",
    "has_alliteration",
    # 4.6 Sentiment and Tone
    "sentiment_polarity",
    "sentiment_subjectivity",
    "is_provocative",
    "has_normative_verb",
    # 4.7 NLP Features
    "noun_ratio",
    "adj_ratio",
    "verb_ratio",
    "named_entity_count",
    "named_entity_density",
    "semantic_similarity_to_journal",
    "abstractness_score",
    # 4.8 Computed Interaction Features
    "length_x_colon",
    "novelty_x_specialty",
    "legal_density_x_rank",
]

_IMPLEMENTED_FEATURES = [
    "char_count",
    "word_count",
    "log_char_count",
    "has_colon",
    "has_question_mark",
    "has_em_dash",
    "has_comma",
    "num_punctuation",
    "subtitle_length_ratio",
    "tmpl_the_x_of_y",
    "tmpl_beyond_x",
    "tmpl_rethinking_x",
    "tmpl_x_in_age_of_y",
    "tmpl_toward_x",
    "tmpl_x_and_y",
    "tmpl_against_x",
    "tmpl_defense_of_x",
    "tmpl_death_of_x",
    "has_case_name",
    "has_statute_ref",
    "has_amendment_ref",
    "has_alliteration",
    "is_provocative",
    "has_normative_verb",
    "length_x_colon",
    # Legacy
    "has_subtitle",
    "title_case_ratio",
    "avg_word_length",
    "punctuation_density",
]

_STUB_FEATURES = [
    "has_jurisdiction",
    "num_legal_terms",
    "legal_term_density",
    "has_neologism",
    "has_pop_culture",
    "has_metaphor_signal",
    "title_novelty_score",
    "sentiment_polarity",
    "sentiment_subjectivity",
    "noun_ratio",
    "adj_ratio",
    "verb_ratio",
    "named_entity_count",
    "named_entity_density",
    "semantic_similarity_to_journal",
    "abstractness_score",
    "novelty_x_specialty",
    "legal_density_x_rank",
    # Legacy
    "flesch_reading_ease",
]


def list_features() -> list[str]:
    """Return names of all implemented (non-stub) features."""
    return list(_IMPLEMENTED_FEATURES)


def list_stub_features() -> list[str]:
    """Return names of features not yet implemented (stub only)."""
    return list(_STUB_FEATURES)


def list_section4_features() -> list[str]:
    """Return names of all 40 candidate features from the research design (Section 4)."""
    return list(_SECTION4_FEATURES)
