"""Every sprint change goes through move_stories (MOVE-11), so the rules live in one place."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Sprint, Story, User
from .events import record_change
from .graph import warnings_for
from .sprints import is_closed


def _move_one(db: Session, story: Story, target: Sprint | None, actor: User, status_override: str | None) -> None:
    old_sprint_id, old_status = story.sprint_id, story.status
    new_sprint_id = target.id if target else None
    if status_override:
        new_status = status_override
    elif new_sprint_id == old_sprint_id:
        new_status = old_status
    elif new_sprint_id is None:
        new_status = "backlog"
    elif old_status == "backlog":
        new_status = "selected"
    else:
        new_status = old_status  # MOVE-10: a partly finished story keeps its status
    # Set both so the column is current before flush and the relationship is current for warnings.
    story.sprint_id = new_sprint_id
    story.sprint = target
    story.status = new_status
    record_change(db, story, "sprint_id", old_sprint_id, new_sprint_id, actor.id)
    record_change(db, story, "status", old_status, new_status, actor.id)


def move_stories(
    db: Session,
    stories: list[Story],
    target: Sprint | None,
    actor: User,
    status_override: str | None = None,
) -> list[str]:
    """Moves top-level stories and their unfinished subtasks. Checks every rule before changing anything."""
    if target is not None and is_closed(target):
        raise HTTPException(status_code=400, detail="Sprint is closed")
    for story in stories:
        if target is not None and target.project_id != story.project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")
        if story.parent_story_id is not None:
            raise HTTPException(status_code=400, detail="Subtasks move with their parent story")
        if is_closed(story.sprint) and story.status == "done":
            raise HTTPException(status_code=400, detail="Done stories stay in the closed sprint where they were finished")

    moved: list[Story] = []
    for story in stories:
        _move_one(db, story, target, actor, status_override)
        moved.append(story)
        for subtask in story.subtasks:
            # MOVE-6: unfinished subtasks follow the parent; done ones stay where they were finished.
            if subtask.status != "done" and subtask.sprint_id != story.sprint_id:
                _move_one(db, subtask, target, actor, None)
                moved.append(subtask)
    db.flush()
    return warnings_for(moved)


def unfinished_top_level(db: Session, sprint: Sprint) -> list[Story]:
    return (
        db.query(Story)
        .filter(Story.sprint_id == sprint.id, Story.parent_story_id.is_(None), Story.status != "done")
        .order_by(Story.created_at)
        .all()
    )
