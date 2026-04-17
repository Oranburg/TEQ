"""Tests for the hypothesis registry and audit logging."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from teq.models import AuditLog, Base, ExperimentRun, Hypothesis


# ---------------------------------------------------------------------------
# Fixtures — patch get_session to use an isolated in-memory database.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Replace the database engine with an in-memory SQLite instance for each test."""
    import teq.database as db_module
    import teq.hypothesis as hyp_module

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng)

    from contextlib import contextmanager

    @contextmanager
    def mock_get_session():
        sess = Session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    monkeypatch.setattr(db_module, "engine", eng)
    monkeypatch.setattr(db_module, "get_session", mock_get_session)
    monkeypatch.setattr(hyp_module, "get_session", mock_get_session)

    yield eng

    Base.metadata.drop_all(eng)


@pytest.fixture
def session(isolated_db):
    Session = sessionmaker(bind=isolated_db)
    sess = Session()
    yield sess
    sess.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_register_hypothesis(session):
    """Registering a hypothesis creates a Hypothesis record."""
    from teq.hypothesis import register_hypothesis

    h = register_hypothesis(
        name="word_count_predicts_citations",
        description="Higher word count correlates with more citations.",
        null_hypothesis="Word count has no effect on citation count.",
    )
    assert h.id is not None
    assert h.name == "word_count_predicts_citations"
    assert h.status == "registered"

    result = session.query(Hypothesis).filter_by(name="word_count_predicts_citations").one()
    assert result.status == "registered"


def test_register_hypothesis_audit_log(session):
    """Registering a hypothesis writes an audit log entry."""
    from teq.hypothesis import register_hypothesis

    h = register_hypothesis(
        name="colon_predicts_placement",
        description="Titles with colons are placed in higher-tier journals.",
        null_hypothesis="Colon presence has no effect on placement tier.",
    )

    entry = (
        session.query(AuditLog)
        .filter_by(action="hypothesis_registered", entity_type="Hypothesis")
        .first()
    )
    assert entry is not None
    assert entry.entity_id == h.id
    details = json.loads(entry.details)
    assert details["name"] == "colon_predicts_placement"


def test_log_experiment(session):
    """Logging an experiment creates an ExperimentRun and an audit entry."""
    from teq.hypothesis import log_experiment, register_hypothesis

    h = register_hypothesis(
        name="h_test_experiment",
        description="desc",
        null_hypothesis="null",
    )

    run = log_experiment(
        hypothesis_id=h.id,
        description="OLS regression on word count",
        parameters={"feature": "word_count", "alpha": 0.05},
        results={"r_squared": 0.12, "beta": 0.03},
        p_value=0.04,
        effect_size=0.15,
        notes="Preliminary run.",
    )

    assert run.id is not None
    assert run.hypothesis_id == h.id
    assert run.p_value == pytest.approx(0.04)

    db_run = session.query(ExperimentRun).filter_by(id=run.id).one()
    assert db_run.description == "OLS regression on word count"
    params = json.loads(db_run.parameters)
    assert params["feature"] == "word_count"


def test_log_experiment_audit_log(session):
    """Logging an experiment writes an audit log entry."""
    from teq.hypothesis import log_experiment, register_hypothesis

    h = register_hypothesis(name="h_audit_test", description="d", null_hypothesis="n")
    run = log_experiment(
        hypothesis_id=h.id,
        description="test run",
        parameters={},
        results={},
    )

    entry = (
        session.query(AuditLog)
        .filter_by(action="experiment_run", entity_type="ExperimentRun")
        .first()
    )
    assert entry is not None
    assert entry.entity_id == run.id


def test_list_hypotheses_no_filter(session):
    """list_hypotheses() without filter returns all hypotheses."""
    from teq.hypothesis import list_hypotheses, register_hypothesis

    register_hypothesis("h1", "d1", "n1")
    register_hypothesis("h2", "d2", "n2")

    results = list_hypotheses()
    names = [h.name for h in results]
    assert "h1" in names
    assert "h2" in names


def test_list_hypotheses_status_filter(session):
    """list_hypotheses(status=...) filters correctly."""
    from teq.hypothesis import list_hypotheses, register_hypothesis, update_hypothesis_status

    h1 = register_hypothesis("h_registered", "d", "n")
    h2 = register_hypothesis("h_rejected", "d", "n")
    update_hypothesis_status(h2.id, "rejected")

    registered = list_hypotheses(status="registered")
    rejected = list_hypotheses(status="rejected")

    assert any(h.name == "h_registered" for h in registered)
    assert not any(h.name == "h_rejected" for h in registered)
    assert any(h.name == "h_rejected" for h in rejected)


def test_update_hypothesis_status(session):
    """update_hypothesis_status() changes status and logs the change."""
    from teq.hypothesis import register_hypothesis, update_hypothesis_status

    h = register_hypothesis("h_status_test", "desc", "null")
    updated = update_hypothesis_status(h.id, "confirmed")

    assert updated.status == "confirmed"
    assert updated.tested_at is not None

    entry = (
        session.query(AuditLog)
        .filter_by(action="hypothesis_status_updated", entity_type="Hypothesis")
        .first()
    )
    assert entry is not None
    details = json.loads(entry.details)
    assert details["new_status"] == "confirmed"
