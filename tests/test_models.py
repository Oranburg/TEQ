"""Tests for SQLAlchemy ORM models and database initialization."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from teq.models import Article, Base, Journal, TitleFeature


@pytest.fixture
def engine():
    """In-memory SQLite engine for isolated tests."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def test_init_db_creates_tables(engine):
    """init_db() equivalent: Base.metadata.create_all creates all expected tables."""
    table_names = set(Base.metadata.tables.keys())
    assert "journals" in table_names
    assert "articles" in table_names
    assert "title_features" in table_names
    assert "hypotheses" in table_names
    assert "experiment_runs" in table_names
    assert "audit_log" in table_names


def test_create_and_read_journal(session):
    """Can create a Journal and read it back."""
    journal = Journal(
        name="Harvard Law Review",
        wl_id="HLR-001",
        rank=1,
        combined_score=95.0,
        category="General",
    )
    session.add(journal)
    session.commit()

    result = session.query(Journal).filter_by(name="Harvard Law Review").one()
    assert result.rank == 1
    assert result.combined_score == 95.0
    assert result.wl_id == "HLR-001"
    assert result.category == "General"


def test_create_and_read_article(session):
    """Can create an Article linked to a Journal and read it back."""
    journal = Journal(name="Yale Law Journal", rank=2)
    session.add(journal)
    session.flush()

    article = Article(
        title="The Rise and Fall of Securities Regulation",
        journal_id=journal.id,
        year=2023,
        citation_count=42,
    )
    session.add(article)
    session.commit()

    result = session.query(Article).filter_by(
        title="The Rise and Fall of Securities Regulation"
    ).one()
    assert result.journal_id == journal.id
    assert result.year == 2023
    assert result.citation_count == 42


def test_create_and_read_title_feature(session):
    """Can create a TitleFeature linked to an Article and read it back."""
    journal = Journal(name="Stanford Law Review", rank=3)
    session.add(journal)
    session.flush()

    article = Article(title="Corporations", journal_id=journal.id)
    session.add(article)
    session.flush()

    feature = TitleFeature(
        article_id=article.id,
        feature_name="word_count",
        feature_value=1.0,
        extraction_version="0.1.0",
    )
    session.add(feature)
    session.commit()

    result = session.query(TitleFeature).filter_by(
        article_id=article.id, feature_name="word_count"
    ).one()
    assert result.feature_value == 1.0
    assert result.extraction_version == "0.1.0"


def test_title_feature_unique_constraint(session):
    """TitleFeature enforces unique constraint on (article_id, feature_name, extraction_version)."""
    journal = Journal(name="Columbia Law Review", rank=4)
    session.add(journal)
    session.flush()

    article = Article(title="Is Law Dead?", journal_id=journal.id)
    session.add(article)
    session.flush()

    feature1 = TitleFeature(
        article_id=article.id,
        feature_name="word_count",
        feature_value=3.0,
        extraction_version="0.1.0",
    )
    session.add(feature1)
    session.commit()

    # Attempt to insert a duplicate — should raise IntegrityError.
    feature2 = TitleFeature(
        article_id=article.id,
        feature_name="word_count",
        feature_value=3.0,
        extraction_version="0.1.0",
    )
    session.add(feature2)
    with pytest.raises(IntegrityError):
        session.commit()
