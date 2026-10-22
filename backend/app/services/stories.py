"""Story rules and serialization shared by the story, board, planning and sprint routers."""

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..models import Comment, Dependency, ProjectMember, Sprint, Story, StoryEvent, User
from ..schemas.stories import CommentRead, DependencyRead, SprintHistoryEntry, StoryDetail, StorySummary
from . import clock
from .github_links import branch_url, suggested_branch
from .graph import warnings_for

PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


def backlog_order(story: Story):
    """Priority first, then oldest first (CORE-11)."""
    return (PRIORITY_ORDER.get(story.priority, 9), story.created_at, story.id)


def summary_options():
    return (
        selectinload(Story.blocked_by_links).selectinload(Dependency.blocker),
        selectinload(Story.subtasks),
    )


def ensure_title_available(db: Session, project_id: str, title: str, exclude_id: str | None = None) -> None:
    query = db.query(Story).filter(Story.project_id == project_id, func.lower(Story.title) == title.lower())
    if exclude_id:
        query = query.filter(Story.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="A story with this title already exists in this project")


def ensure_assignee_is_member(db: Session, project_id: str, assignee_id: str | None) -> None:
    if not assignee_id:
        return
    if not db.query(ProjectMember).filter_by(project_id=project_id, user_id=assignee_id).first():
        raise HTTPException(status_code=400, detail="Assignee must be a project member")


def carryover_counts(db: Session, story_ids: list[str]) -> dict[str, int]:
    """Moves out of a sprint after it started while the story wasn't done (MOVE-8)."""
    if not story_ids:
        return {}
    events = (
        db.query(StoryEvent)
        .filter(
            StoryEvent.story_id.in_(story_ids),
            StoryEvent.event_type.in_(("status_changed", "sprint_changed")),
        )
        .order_by(StoryEvent.created_at)
        .all()
    )
    sprint_ids = {event.from_value for event in events if event.event_type == "sprint_changed" and event.from_value}
    starts = {}
    if sprint_ids:
        rows = db.query(Sprint).execution_options(include_deleted=True).filter(Sprint.id.in_(sprint_ids)).all()
        starts = {sprint.id: clock.start_of_day(sprint.start_date) for sprint in rows}
    counts = {story_id: 0 for story_id in story_ids}
    status: dict[str, str | None] = {}
    for event in events:
        if event.event_type == "status_changed":
            status[event.story_id] = event.to_value
        elif event.from_value and event.from_value in starts:
            if event.created_at >= starts[event.from_value] and status.get(event.story_id) != "done":
                counts[event.story_id] += 1
    return counts


def story_summary(story: Story, carryover: int = 0) -> StorySummary:
    blockers = [link.blocker for link in story.blocked_by_links if link.blocker is not None]
    return StorySummary(
        id=story.id,
        project_id=story.project_id,
        sprint_id=story.sprint_id,
        parent_story_id=story.parent_story_id,
        title=story.title,
        status=story.status,
        priority=story.priority,
        story_points=story.story_points,
        assignee_id=story.assignee_id,
        due_date=story.due_date,
        github_branch=story.github_branch,
        blocked_by=[blocker.id for blocker in blockers],
        blocked_by_titles=[blocker.title for blocker in blockers],
        all_blockers_done=bool(blockers) and all(blocker.status == "done" for blocker in blockers),
        subtask_count=len(story.subtasks),
        carryover_count=carryover,
    )


def story_summaries(db: Session, stories: list[Story]) -> list[StorySummary]:
    counts = carryover_counts(db, [story.id for story in stories])
    return [story_summary(story, counts.get(story.id, 0)) for story in stories]


def dependency_read(link: Dependency) -> DependencyRead:
    return DependencyRead(
        id=link.id,
        blocker_story_id=link.blocker_story_id,
        blocked_story_id=link.blocked_story_id,
        blocker_title=link.blocker.title,
        blocked_title=link.blocked.title,
        blocker_status=link.blocker.status,
        reason=link.reason,
        created_at=link.created_at,
    )


def comment_read(comment: Comment) -> CommentRead:
    return CommentRead(
        id=comment.id,
        story_id=comment.story_id,
        author_id=comment.author_id,
        author_name=comment.author.name,
        text=comment.text,
        created_at=comment.created_at,
    )


def sprint_history(db: Session, story: Story) -> list[SprintHistoryEntry]:
    events = (
        db.query(StoryEvent)
        .options(selectinload(StoryEvent.actor))
        .filter(StoryEvent.story_id == story.id, StoryEvent.event_type == "sprint_changed")
        .order_by(StoryEvent.created_at)
        .all()
    )
    sprint_ids = {event.to_value for event in events if event.to_value}
    names = {}
    if sprint_ids:
        rows = db.query(Sprint).execution_options(include_deleted=True).filter(Sprint.id.in_(sprint_ids)).all()
        names = {sprint.id: sprint.name for sprint in rows}
    return [
        SprintHistoryEntry(
            sprint_id=event.to_value,
            sprint_name=names.get(event.to_value, "Unknown sprint") if event.to_value else "Backlog",
            moved_at=event.created_at,
            moved_by_name=event.actor.name if event.actor else None,
        )
        for event in events
    ]


def story_detail(db: Session, story: Story, current_user: User) -> StoryDetail:
    story = (
        db.query(Story)
        .options(
            selectinload(Story.subtasks).selectinload(Story.blocked_by_links).selectinload(Dependency.blocker),
            selectinload(Story.comments).selectinload(Comment.author),
            selectinload(Story.blocks).selectinload(Dependency.blocked).selectinload(Story.sprint),
            selectinload(Story.blocked_by_links).selectinload(Dependency.blocker).selectinload(Story.sprint),
        )
        .filter(Story.id == story.id)
        .populate_existing()
        .one()
    )
    counts = carryover_counts(db, [story.id, *[subtask.id for subtask in story.subtasks]])
    summary = story_summary(story, counts.get(story.id, 0))
    username = story.assignee.username if story.assignee else current_user.username
    repo_url = story.project.github_repo_url
    return StoryDetail(
        **summary.model_dump(),
        description=story.description,
        acceptance_criteria=story.acceptance_criteria,
        created_at=story.created_at,
        updated_at=story.updated_at,
        parent_title=story.parent.title if story.parent else None,
        sprint_name=story.sprint.name if story.sprint else None,
        sprint_closed=bool(story.sprint and story.sprint.closed_at),
        branch_url=branch_url(repo_url, story.github_branch),
        suggested_branch=suggested_branch(username, story.title),
        subtasks=[story_summary(subtask, counts.get(subtask.id, 0)) for subtask in story.subtasks],
        comments=[comment_read(comment) for comment in story.comments],
        blocks=[dependency_read(link) for link in story.blocks if link.blocked is not None],
        blocked_by_links=[dependency_read(link) for link in story.blocked_by_links if link.blocker is not None],
        sprint_history=sprint_history(db, story),
        warnings=warnings_for([story]),
    )
