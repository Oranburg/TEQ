"""Tests for the feature extraction module."""

from __future__ import annotations

import pytest

from teq.features import extract_features, list_features, list_stub_features


def test_corporations_title():
    """Single-word title: word_count=1, no colon, no question mark."""
    features = extract_features("Corporations")
    assert features["word_count"] == 1.0
    assert features["has_colon"] == 0.0
    assert features["has_question_mark"] == 0.0
    assert features["has_subtitle"] == 0.0


def test_title_with_colon_and_question_mark():
    """Title with both colon and question mark."""
    features = extract_features("Is Law Dead?: A Symposium")
    assert features["has_colon"] == 1.0
    assert features["has_question_mark"] == 1.0
    assert features["has_subtitle"] == 1.0


def test_securities_regulation_title():
    """Seven-word title without subtitle markers."""
    features = extract_features("The Rise and Fall of Securities Regulation")
    assert features["word_count"] == 7.0
    assert features["has_subtitle"] == 0.0
    assert features["has_colon"] == 0.0


def test_char_count():
    """char_count equals len(title)."""
    title = "Corporations"
    features = extract_features(title)
    assert features["char_count"] == float(len(title))


def test_has_subtitle_em_dash():
    """has_subtitle triggers on em-dash as well as colon."""
    features = extract_features("The Constitution\u2014A Living Document")
    assert features["has_subtitle"] == 1.0


def test_title_case_ratio_all_title_case():
    """All content words title-cased → ratio close to 1.0."""
    features = extract_features("Corporations Rise Again")
    assert features["title_case_ratio"] == pytest.approx(1.0)


def test_title_case_ratio_mixed():
    """Stop words excluded; partial title case gives correct ratio."""
    # "The" is a stop word; "rise" is lowercase → ratio = 2/3
    features = extract_features("The Rise and fall of Securities")
    # Content words (excluding stop words 'the', 'and', 'of'): Rise, fall, Securities
    # Title-cased: Rise, Securities → 2/3
    assert features["title_case_ratio"] == pytest.approx(2 / 3, abs=0.01)


def test_list_features_nonempty():
    """list_features() returns a non-empty list."""
    features = list_features()
    assert isinstance(features, list)
    assert len(features) > 0


def test_list_stub_features_nonempty():
    """list_stub_features() returns a non-empty list."""
    stubs = list_stub_features()
    assert isinstance(stubs, list)
    assert len(stubs) > 0


def test_all_implemented_features_are_float():
    """Every feature returned by extract_features() is a float."""
    features = extract_features("Administrative Law: A Modern Approach?")
    for name, value in features.items():
        assert isinstance(value, float), f"Feature '{name}' is not a float: {value!r}"


def test_implemented_features_in_list_features():
    """All names in list_features() appear in extract_features() output."""
    output = extract_features("Any title works here")
    for name in list_features():
        assert name in output, f"Feature '{name}' missing from extract_features() output"


def test_stub_features_return_zero():
    """All stub features currently return 0.0."""
    features = extract_features("Test Title")
    for name in list_stub_features():
        assert features[name] == 0.0, f"Stub feature '{name}' should return 0.0"
