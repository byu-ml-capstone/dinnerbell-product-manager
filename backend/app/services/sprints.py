"""Sprint status is worked out from the dates; closing is the only stored state (CORE-13)."""

from datetime import date

from sqlalchemy.orm import Session

from ..models import Sprint, Story
from ..schemas.sprints import SprintRead
from . import clock


def sprint_status(sprint: Sprint, today: date | None = None) -> str:
    today = today or clock.today()
    if sprint.closed_at is not None:
        return "closed"
    if sprint.start_date > today:
        return "planned"
    return "active"


def is_overdue(sprint: Sprint, today: date | None = None) -> bool:
    today = today or clock.today()
    return sprint_status(sprint, today) == "active" and sprint.end_date < today


def is_closed(sprint: Sprint | None) -> bool:
    return sprint is not None and sprint.closed_at is not None


def serialize_sprints(db: Session, sprints: list[Sprint]) -> list[SprintRead]:
    ids = [sprint.id for sprint in sprints]
    stories = (
        db.query(Story).filter(Story.sprint_id.in_(ids), Story.parent_story_id.is_(None)).all() if ids else []
    )
    by_sprint: dict[str, list[Story]] = {sprint_id: [] for sprint_id in ids}
    for story in stories:
        by_sprint[story.sprint_id].append(story)
    today = clock.today()
    from .metrics import average_velocity, capacity_warning  # metrics imports this module

    averages = {project_id: average_velocity(db, project_id) for project_id in {sprint.project_id for sprint in sprints}}
    result = []
    for sprint in sprints:
        top_level = by_sprint[sprint.id]
        planned = sum(story.story_points or 0 for story in top_level)
        result.append(
            SprintRead(
                id=sprint.id,
                project_id=sprint.project_id,
                name=sprint.name,
                goal=sprint.goal,
                status=sprint_status(sprint, today),
                is_overdue=is_overdue(sprint, today),
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                closed_at=sprint.closed_at,
                closed_by_id=sprint.closed_by_id,
                velocity=sprint.velocity,
                committed_points=sprint.committed_points,
                notes=sprint.notes,
                story_count=len(top_level),
                planned_points=planned,
                completed_points=sum(story.story_points or 0 for story in top_level if story.status == "done"),
                capacity_warning=None if sprint.closed_at else capacity_warning(planned, averages[sprint.project_id]),
                created_at=sprint.created_at,
            )
        )
    return result


def serialize_sprint(db: Session, sprint: Sprint) -> SprintRead:
    return serialize_sprints(db, [sprint])[0]
