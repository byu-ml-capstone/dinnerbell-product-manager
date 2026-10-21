from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_project_for_member
from ..models import Sprint, Story, User
from ..schemas.metrics import ClosedWithUnfinished, PlanningRead, PlanningSprint
from ..services.sprints import is_closed, serialize_sprints
from ..services.stories import backlog_order, story_summaries, summary_options

router = APIRouter(prefix="/api", tags=["planning"])


@router.get("/projects/{project_id}/planning", response_model=PlanningRead)
def planning(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> PlanningRead:
    project = get_project_for_member(db, project_id, user)
    sprints = db.query(Sprint).filter(Sprint.project_id == project.id).order_by(Sprint.start_date, Sprint.created_at).all()
    # Subtasks move with their parent (MOVE-6), so planning only shows top-level stories.
    stories = (
        db.query(Story)
        .options(*summary_options())
        .filter(Story.project_id == project.id, Story.parent_story_id.is_(None))
        .all()
    )
    summaries = {summary.id: summary for summary in story_summaries(db, stories)}
    by_sprint: dict[str | None, list] = {}
    for story in sorted(stories, key=backlog_order):
        by_sprint.setdefault(story.sprint_id, []).append(summaries[story.id])

    serialized = {item.id: item for item in serialize_sprints(db, sprints)}
    open_sprints = [sprint for sprint in sprints if not is_closed(sprint)]
    closed = [sprint for sprint in sprints if is_closed(sprint)]
    unfinished = {
        sprint.id: sum(1 for summary in by_sprint.get(sprint.id, []) if summary.status != "done") for sprint in closed
    }
    return PlanningRead(
        backlog=by_sprint.get(None, []),
        sprints=[
            PlanningSprint(
                sprint=serialized[sprint.id],
                stories=by_sprint.get(sprint.id, []),
                capacity_warning=serialized[sprint.id].capacity_warning,
            )
            for sprint in open_sprints
        ],
        closed_with_unfinished=[
            ClosedWithUnfinished(sprint=serialized[sprint.id], unfinished_count=unfinished[sprint.id])
            for sprint in closed
            if unfinished[sprint.id]
        ],
    )
