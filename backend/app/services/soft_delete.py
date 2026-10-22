"""Soft delete and batch restore (§7). Children go with their parent in one batch and come back with it (D-26)."""

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..models import Comment, DeletionBatch, Dependency, Project, Sprint, SprintMessage, Story, User
from . import clock
from .events import record_change, record_story_event
from .graph import find_cycle
from .sprints import is_closed

COUNT_KEYS = {
    Project: "projects",
    Sprint: "sprints",
    Story: "stories",
    Dependency: "dependencies",
    Comment: "comments",
    SprintMessage: "messages",
}
ROOT_TYPES = {"project": Project, "sprint": Sprint, "story": Story, "dependency": Dependency, "message": SprintMessage}


def _start_batch(db: Session, project_id: str, root_type: str, root_id: str, label: str, actor: User) -> DeletionBatch:
    batch = DeletionBatch(
        project_id=project_id,
        root_type=root_type,
        root_id=root_id,
        root_label=label[:255],
        counts={},
        deleted_by_id=actor.id,
        deleted_at=clock.now(),
    )
    db.add(batch)
    db.flush()
    return batch


def _finish_batch(db: Session, batch: DeletionBatch, rows: list, actor: User) -> DeletionBatch:
    unique_rows = list({(type(row), row.id): row for row in rows if row.deleted_at is None}.values())
    counts: dict[str, int] = {}
    for row in unique_rows:
        row.deleted_at = batch.deleted_at
        row.deleted_by_id = actor.id
        row.deletion_batch_id = batch.id
        key = COUNT_KEYS[type(row)]
        counts[key] = counts.get(key, 0) + 1
        if isinstance(row, Story):
            record_story_event(db, row, "deleted", None, None, actor.id)
    # Report children only; the root itself is implied by the label.
    root_key = COUNT_KEYS[ROOT_TYPES[batch.root_type]]
    counts[root_key] = counts.get(root_key, 1) - 1
    batch.counts = {key: value for key, value in counts.items() if value}
    db.flush()
    return batch


def _story_children(db: Session, story_ids: set[str]) -> list:
    if not story_ids:
        return []
    comments = db.query(Comment).filter(Comment.story_id.in_(story_ids)).all()
    links = (
        db.query(Dependency)
        .filter(or_(Dependency.blocker_story_id.in_(story_ids), Dependency.blocked_story_id.in_(story_ids)))
        .all()
    )
    return [*comments, *links]


def _with_subtasks(db: Session, stories: list[Story]) -> list[Story]:
    ids = {story.id for story in stories}
    subtasks = db.query(Story).filter(Story.parent_story_id.in_(ids)).all() if ids else []
    return [*stories, *[subtask for subtask in subtasks if subtask.id not in ids]]


def delete_story(db: Session, story: Story, actor: User) -> DeletionBatch:
    if is_closed(story.sprint):
        raise HTTPException(status_code=400, detail="Stories in a closed sprint can't be deleted")
    stories = _with_subtasks(db, [story])
    batch = _start_batch(db, story.project_id, "story", story.id, story.title, actor)
    return _finish_batch(db, batch, [*stories, *_story_children(db, {item.id for item in stories})], actor)


def delete_sprint(db: Session, sprint: Sprint, actor: User) -> DeletionBatch:
    stories = _with_subtasks(db, db.query(Story).filter(Story.sprint_id == sprint.id).all())
    messages = db.query(SprintMessage).filter(SprintMessage.sprint_id == sprint.id).all()
    batch = _start_batch(db, sprint.project_id, "sprint", sprint.id, sprint.name, actor)
    rows = [sprint, *stories, *_story_children(db, {story.id for story in stories}), *messages]
    return _finish_batch(db, batch, rows, actor)


def delete_project(db: Session, project: Project, actor: User) -> DeletionBatch:
    sprints = db.query(Sprint).filter(Sprint.project_id == project.id).all()
    stories = db.query(Story).filter(Story.project_id == project.id).all()
    sprint_ids = [sprint.id for sprint in sprints]
    messages = db.query(SprintMessage).filter(SprintMessage.sprint_id.in_(sprint_ids)).all() if sprint_ids else []
    batch = _start_batch(db, project.id, "project", project.id, project.name, actor)
    rows = [project, *sprints, *stories, *_story_children(db, {story.id for story in stories}), *messages]
    return _finish_batch(db, batch, rows, actor)


def delete_dependency(db: Session, link: Dependency, actor: User) -> DeletionBatch:
    label = f"Link: {link.blocker.title} blocks {link.blocked.title}"
    batch = _start_batch(db, link.blocked.project_id, "dependency", link.id, label, actor)
    return _finish_batch(db, batch, [link], actor)


def delete_message(db: Session, message: SprintMessage, sprint: Sprint, actor: User) -> DeletionBatch:
    replies = db.query(SprintMessage).filter(SprintMessage.parent_message_id == message.id).all()
    label = message.text if len(message.text) <= 60 else f"{message.text[:57]}..."
    batch = _start_batch(db, sprint.project_id, "message", message.id, f"Message: {label}", actor)
    return _finish_batch(db, batch, [message, *replies], actor)


def _rows_in_batch(db: Session, model, batch_id: str) -> list:
    return db.query(model).execution_options(include_deleted=True).filter(model.deletion_batch_id == batch_id).all()


def _get_any(db: Session, model, row_id: str | None):
    if row_id is None:
        return None
    return db.query(model).execution_options(include_deleted=True).filter(model.id == row_id).first()


def restore_batch(db: Session, batch: DeletionBatch, actor: User) -> dict[str, int]:
    if batch.restored_at is not None:
        raise HTTPException(status_code=409, detail="This item was already restored")
    rows = {model: _rows_in_batch(db, model, batch.id) for model in COUNT_KEYS}
    in_batch = {(model, row.id) for model, items in rows.items() for row in items}

    def deleted_elsewhere(model, row_id: str | None) -> bool:
        row = _get_any(db, model, row_id)
        return row is not None and row.deleted_at is not None and (model, row.id) not in in_batch

    if batch.root_type != "project" and deleted_elsewhere(Project, batch.project_id):
        raise HTTPException(status_code=409, detail="Restore the project first")

    for story in rows[Story]:
        clash = (
            db.query(Story)
            .filter(Story.project_id == story.project_id, func.lower(Story.title) == story.title.lower(), Story.id != story.id)
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"A story titled '{story.title}' already exists. Rename it before restoring.",
            )
        if story.parent_story_id and deleted_elsewhere(Story, story.parent_story_id):
            raise HTTPException(status_code=409, detail="Restore the parent story first")

    for message in rows[SprintMessage]:
        if deleted_elsewhere(Sprint, message.sprint_id):
            raise HTTPException(status_code=409, detail="Restore the sprint first")
        if message.parent_message_id and deleted_elsewhere(SprintMessage, message.parent_message_id):
            raise HTTPException(status_code=409, detail="Restore the original post first")

    if batch.root_type == "dependency":
        link = rows[Dependency][0]
        if deleted_elsewhere(Story, link.blocker_story_id) or deleted_elsewhere(Story, link.blocked_story_id):
            raise HTTPException(status_code=409, detail="Both stories must exist to restore this link")
        duplicate = (
            db.query(Dependency)
            .filter_by(blocker_story_id=link.blocker_story_id, blocked_story_id=link.blocked_story_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="These stories are already linked")
        blocked = _get_any(db, Story, link.blocked_story_id)
        if find_cycle(db, blocked.project_id, link.blocker_story_id, link.blocked_story_id):
            raise HTTPException(status_code=409, detail="Restoring this link would create a cycle")

    restored: dict[str, int] = {}
    for model, items in rows.items():
        for row in items:
            if model is Dependency and batch.root_type != "dependency":
                # A link whose other story is still deleted waits for that story's batch instead.
                other_deleted = [
                    _get_any(db, Story, story_id)
                    for story_id in (row.blocker_story_id, row.blocked_story_id)
                    if deleted_elsewhere(Story, story_id)
                ]
                if other_deleted:
                    row.deletion_batch_id = other_deleted[0].deletion_batch_id
                    continue
            row.deleted_at = None
            row.deleted_by_id = None
            row.deletion_batch_id = None
            restored[COUNT_KEYS[model]] = restored.get(COUNT_KEYS[model], 0) + 1

    for story in rows[Story]:
        record_story_event(db, story, "restored", None, None, actor.id)
        if story.sprint_id and deleted_elsewhere(Sprint, story.sprint_id):
            # DEL-6: the story's sprint is still deleted, so it comes back to the backlog.
            old_sprint, old_status = story.sprint_id, story.status
            story.sprint_id = None
            story.status = "backlog"
            record_change(db, story, "sprint_id", old_sprint, None, actor.id)
            record_change(db, story, "status", old_status, "backlog", actor.id)

    batch.restored_at = clock.now()
    batch.restored_by_id = actor.id
    db.flush()
    return restored
