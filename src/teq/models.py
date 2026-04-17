"""SQLAlchemy ORM models for the TEQ research database."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Journal(Base):
    """A law review journal entry from W&L rankings data."""

    __tablename__ = "journals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wl_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    combined_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    journals_cited: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cases_cited: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # General, Specialized
    editing: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Student-Edited, Peer-Edited, Refereed
    format: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Print, Online
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    school: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="journal"
    )


class Article(Base):
    """A law review article with title and impact metadata."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    journal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("journals.id"), nullable=True
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    authors: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # semicolon-delimited for v1
    citation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    placement_tier: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1–5 or similar
    doi: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    journal: Mapped[Optional["Journal"]] = relationship(
        "Journal", back_populates="articles"
    )
    features: Mapped[list["TitleFeature"]] = relationship(
        "TitleFeature", back_populates="article"
    )


class TitleFeature(Base):
    """A single extracted feature for an article title."""

    __tablename__ = "title_features"

    __table_args__ = (
        UniqueConstraint(
            "article_id", "feature_name", "extraction_version", name="uq_feature"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=False
    )
    feature_name: Mapped[str] = mapped_column(String, nullable=False)
    feature_value: Mapped[float] = mapped_column(Float, nullable=False)
    extraction_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    article: Mapped["Article"] = relationship("Article", back_populates="features")


class Hypothesis(Base):
    """A pre-registered research hypothesis."""

    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    null_hypothesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String, default="registered", nullable=False
    )  # registered, testing, confirmed, rejected, inconclusive
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    tested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    experiment_runs: Mapped[list["ExperimentRun"]] = relationship(
        "ExperimentRun", back_populates="hypothesis"
    )


class ExperimentRun(Base):
    """A logged experiment or statistical test."""

    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hypothesis_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("hypotheses.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    p_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    effect_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    hypothesis: Mapped[Optional["Hypothesis"]] = relationship(
        "Hypothesis", back_populates="experiment_runs"
    )


class AuditLog(Base):
    """Immutable audit log for all research actions."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(
        String, nullable=False
    )  # e.g. "hypothesis_registered", "experiment_run"
    entity_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
