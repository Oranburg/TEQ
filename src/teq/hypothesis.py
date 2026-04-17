"""Hypothesis registry for TEQ.

Every hypothesis must be pre-registered before any experiments reference it.
All actions are logged to the AuditLog.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from teq.database import get_session
from teq.models import AuditLog, ExperimentRun, Hypothesis


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    session,
    action: str,
    entity_type: str,
    entity_id: int,
    details: dict,
) -> None:
    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details),
    )
    session.add(log)


def register_hypothesis(
    name: str, description: str, null_hypothesis: str
) -> Hypothesis:
    """Register a new hypothesis. Must be called BEFORE any testing."""
    with get_session() as session:
        hypothesis = Hypothesis(
            name=name,
            description=description,
            null_hypothesis=null_hypothesis,
            status="registered",
            registered_at=_utcnow(),
        )
        session.add(hypothesis)
        session.flush()  # assign id before audit
        _audit(
            session,
            action="hypothesis_registered",
            entity_type="Hypothesis",
            entity_id=hypothesis.id,
            details={"name": name, "description": description},
        )
        session.expunge(hypothesis)
        return hypothesis


def list_hypotheses(status: Optional[str] = None) -> list[Hypothesis]:
    """List all hypotheses, optionally filtered by status."""
    with get_session() as session:
        query = session.query(Hypothesis)
        if status is not None:
            query = query.filter(Hypothesis.status == status)
        results = query.all()
        for h in results:
            session.expunge(h)
        return results


def log_experiment(
    hypothesis_id: Optional[int],
    description: str,
    parameters: dict,
    results: dict,
    p_value: Optional[float] = None,
    effect_size: Optional[float] = None,
    notes: Optional[str] = None,
) -> ExperimentRun:
    """Log an experiment run. Links to a hypothesis if provided."""
    with get_session() as session:
        run = ExperimentRun(
            hypothesis_id=hypothesis_id,
            description=description,
            parameters=json.dumps(parameters),
            results=json.dumps(results),
            p_value=p_value,
            effect_size=effect_size,
            notes=notes,
            run_at=_utcnow(),
        )
        session.add(run)
        session.flush()
        _audit(
            session,
            action="experiment_run",
            entity_type="ExperimentRun",
            entity_id=run.id,
            details={
                "hypothesis_id": hypothesis_id,
                "description": description,
                "p_value": p_value,
            },
        )
        session.expunge(run)
        return run


def update_hypothesis_status(hypothesis_id: int, new_status: str) -> Hypothesis:
    """Update hypothesis status after testing."""
    valid_statuses = {"registered", "testing", "confirmed", "rejected", "inconclusive"}
    if new_status not in valid_statuses:
        raise ValueError(
            f"Invalid status '{new_status}'. Must be one of: {valid_statuses}"
        )
    with get_session() as session:
        hypothesis = session.get(Hypothesis, hypothesis_id)
        if hypothesis is None:
            raise ValueError(f"Hypothesis {hypothesis_id} not found.")
        old_status = hypothesis.status
        hypothesis.status = new_status
        if new_status in {"confirmed", "rejected", "inconclusive"}:
            hypothesis.tested_at = _utcnow()
        _audit(
            session,
            action="hypothesis_status_updated",
            entity_type="Hypothesis",
            entity_id=hypothesis_id,
            details={"old_status": old_status, "new_status": new_status},
        )
        session.flush()
        session.expunge(hypothesis)
        return hypothesis
