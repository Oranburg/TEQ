"""Overseer module — research integrity checks and bias detection for TEQ."""

from __future__ import annotations

from teq.database import get_session
from teq.models import AuditLog, ExperimentRun, Hypothesis


def check_hypothesis_registered(hypothesis_id: int) -> bool:
    """Verify a hypothesis was registered before any experiment references it."""
    with get_session() as session:
        hypothesis = session.get(Hypothesis, hypothesis_id)
        if hypothesis is None:
            return False
        # Check that a "hypothesis_registered" audit entry exists for this id.
        audit_entry = (
            session.query(AuditLog)
            .filter(
                AuditLog.action == "hypothesis_registered",
                AuditLog.entity_type == "Hypothesis",
                AuditLog.entity_id == hypothesis_id,
            )
            .first()
        )
        return audit_entry is not None


def check_multiple_comparisons(
    hypothesis_id: int, alpha: float = 0.05
) -> dict:
    """Check if multiple experiments on the same hypothesis suggest p-hacking.

    Returns a dict with a 'warning' key if the number of runs is suspicious.
    The threshold is based on the expected false-positive rate: if you run N
    independent tests at level alpha, you expect alpha*N false positives.
    A warning is raised when there are enough runs that at least one
    false positive is almost certain (N > 1/alpha).
    """
    with get_session() as session:
        runs = (
            session.query(ExperimentRun)
            .filter(ExperimentRun.hypothesis_id == hypothesis_id)
            .all()
        )
        n_runs = len(runs)
        significant_runs = [
            r for r in runs if r.p_value is not None and r.p_value < alpha
        ]
        n_significant = len(significant_runs)

    result: dict = {
        "hypothesis_id": hypothesis_id,
        "n_runs": n_runs,
        "n_significant": n_significant,
        "alpha": alpha,
    }

    # Warn if the number of runs exceeds the reciprocal of alpha (Bonferroni threshold).
    if n_runs > int(1 / alpha):
        result["warning"] = (
            f"Hypothesis {hypothesis_id} has been tested {n_runs} times. "
            f"At alpha={alpha}, this creates a high risk of false positives. "
            "Apply Bonferroni or FDR correction."
        )

    # Also warn if there are many runs but only cherry-picked significant ones are reported.
    if n_runs >= 3 and n_significant > 0 and n_significant / n_runs < 0.2:
        result["cherry_pick_warning"] = (
            f"Only {n_significant}/{n_runs} runs are significant — "
            "possible selective reporting."
        )

    return result


def check_experiment_logged(run_id: int) -> bool:
    """Verify an experiment run exists in the audit log."""
    with get_session() as session:
        audit_entry = (
            session.query(AuditLog)
            .filter(
                AuditLog.action == "experiment_run",
                AuditLog.entity_type == "ExperimentRun",
                AuditLog.entity_id == run_id,
            )
            .first()
        )
        return audit_entry is not None


def generate_integrity_report() -> str:
    """Generate a plain-text report on research integrity.

    Includes:
    - Number of hypotheses by status
    - Number of experiment runs
    - Any warnings (unregistered tests, suspicious patterns)
    """
    with get_session() as session:
        all_hypotheses = session.query(Hypothesis).all()
        all_runs = session.query(ExperimentRun).all()
        all_audit = session.query(AuditLog).all()

        status_counts: dict[str, int] = {}
        for h in all_hypotheses:
            status_counts[h.status] = status_counts.get(h.status, 0) + 1

        # Check for experiment runs with no matching hypothesis registration.
        registered_ids = {
            entry.entity_id
            for entry in all_audit
            if entry.action == "hypothesis_registered"
            and entry.entity_type == "Hypothesis"
        }
        unregistered_warnings = []
        for run in all_runs:
            if run.hypothesis_id is not None and run.hypothesis_id not in registered_ids:
                unregistered_warnings.append(
                    f"  - ExperimentRun {run.id} references unregistered "
                    f"Hypothesis {run.hypothesis_id}"
                )

        lines = ["=" * 60, "TEQ Research Integrity Report", "=" * 60, ""]

        lines.append("Hypotheses by status:")
        if status_counts:
            for status, count in sorted(status_counts.items()):
                lines.append(f"  {status}: {count}")
        else:
            lines.append("  (none registered)")

        lines.append("")
        lines.append(f"Total experiment runs: {len(all_runs)}")
        lines.append(f"Total audit log entries: {len(all_audit)}")
        lines.append("")

        if unregistered_warnings:
            lines.append("WARNINGS — Unregistered hypothesis references:")
            lines.extend(unregistered_warnings)
            lines.append("")

        # Check each hypothesis for multiple-comparison issues.
        mc_warnings = []
        for h in all_hypotheses:
            report = check_multiple_comparisons(h.id)
            if "warning" in report:
                mc_warnings.append(f"  - {report['warning']}")
            if "cherry_pick_warning" in report:
                mc_warnings.append(f"  - {report['cherry_pick_warning']}")

        if mc_warnings:
            lines.append("WARNINGS — Multiple comparisons / selective reporting:")
            lines.extend(mc_warnings)
            lines.append("")

        if not unregistered_warnings and not mc_warnings:
            lines.append("No integrity warnings detected.")

        lines.append("=" * 60)
        return "\n".join(lines)
