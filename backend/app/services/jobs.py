"""Background AI jobs run in FastAPI BackgroundTasks with their own session (AI-11, REPO-10)."""

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from ..models import SprintAnalysis, SprintReview
from . import clock

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=15)
ACTIVE_STATUSES = ("pending", "running")


def mark_stale_jobs(db: Session) -> int:
    """Called at startup: anything still pending or running for 15+ minutes was killed by a restart."""
    cutoff = clock.now() - STALE_AFTER
    count = 0
    for model in (SprintAnalysis, SprintReview):
        rows = db.query(model).filter(model.status.in_(ACTIVE_STATUSES)).all()
        for row in rows:
            if (row.started_at or row.created_at) < cutoff:
                row.status = "failed"
                row.error = "Interrupted by restart"
                row.completed_at = clock.now()
                count += 1
    db.commit()
    if count:
        logger.warning("Marked %s interrupted AI job(s) as failed", count)
    return count
