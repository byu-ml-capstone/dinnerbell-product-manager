from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_or_404, get_project_for_member, get_story_for_member
from ..models import Sprint, Story, User
from ..schemas.stories import (
    MoveStoriesRequest,
    MoveStoriesResult,
    StoryCreate,
    StoryDetail,
    StorySummary,
    StoryUpdate,
    StoryWriteResult,
)
from ..schemas.trash import DeleteResult
from ..services.events import record_change, record_creation
from ..services.github_links import normalize_branch
from ..services.moves import move_stories
from ..services.soft_delete import delete_story as soft_delete_story
from ..services.sprints import is_closed
from ..services.stories import (
    backlog_order,
    ensure_assignee_is_member,
    ensure_title_available,
    story_detail,
    story_summaries,
    summary_options,
)

router = APIRouter(prefix="/api", tags=["stories"])

TITLE_TAKEN = "A story with this title already exists in this project"
CLOSED_SPRINT = "Story is in a closed sprint; move it out first"


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        # The partial unique index is the last line of defence for titles (CORE-6).
        db.rollback()
        raise HTTPException(status_code=409, detail=TITLE_TAKEN) from exc


def _clean_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title can't be empty")
    return title


def _write_result(db: Session, story: Story, warnings: list[str] | None = None) -> StoryWriteResult:
    db.refresh(story)
    summary = story_summaries(db, [story])[0]
    return StoryWriteResult(**summary.model_dump(), warnings=warnings or [])


def _sprint_in_project(db: Session, sprint_id: str, project_id: str) -> Sprint:
    sprint = get_or_404(db, Sprint, sprint_id, "Sprint")
    if sprint.project_id != project_id:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint


@router.post("/projects/{project_id}/stories", response_model=StoryWriteResult)
def create_story(
    project_id: str,
    payload: StoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoryWriteResult:
    project = get_project_for_member(db, project_id, user)
    title = _clean_title(payload.title)
    ensure_title_available(db, project.id, title)
    ensure_assignee_is_member(db, project.id, payload.assignee_id)
    sprint = None
    if payload.sprint_id:
        sprint = _sprint_in_project(db, payload.sprint_id, project.id)
        if is_closed(sprint):
            raise HTTPException(status_code=400, detail="Sprint is closed")
    story = Story(
        project_id=project.id,
        sprint_id=sprint.id if sprint else None,
        title=title,
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
        status="selected" if sprint else "backlog",
        priority=payload.priority,
        story_points=payload.story_points,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        github_branch=normalize_branch(payload.github_branch, project.github_repo_url),
    )
    db.add(story)
    db.flush()
    record_creation(db, story, user.id)
    _commit(db)
    return _write_result(db, story)


@router.get("/projects/{project_id}/stories", response_model=list[StorySummary])
def list_stories(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[StorySummary]:
    project = get_project_for_member(db, project_id, user)
    stories = db.query(Story).options(*summary_options()).filter(Story.project_id == project.id).all()
    return story_summaries(db, sorted(stories, key=backlog_order))


@router.post("/projects/{project_id}/stories/move", response_model=MoveStoriesResult)
def bulk_move(
    project_id: str,
    payload: MoveStoriesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MoveStoriesResult:
    project = get_project_for_member(db, project_id, user)
    stories = []
    for story_id in dict.fromkeys(payload.story_ids):
        story = get_or_404(db, Story, story_id, "Story")
        if story.project_id != project.id:
            raise HTTPException(status_code=404, detail="Story not found")
        stories.append(story)
    target = _sprint_in_project(db, payload.sprint_id, project.id) if payload.sprint_id else None
    warnings = move_stories(db, stories, target, user)
    db.commit()
    return MoveStoriesResult(stories=story_summaries(db, stories), warnings=warnings)


@router.get("/stories/{story_id}", response_model=StoryDetail)
def get_story(story_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StoryDetail:
    return story_detail(db, get_story_for_member(db, story_id, user), user)


@router.put("/stories/{story_id}", response_model=StoryWriteResult)
def update_story(
    story_id: str,
    payload: StoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoryWriteResult:
    story = get_story_for_member(db, story_id, user)
    data = payload.model_dump(exclude_unset=True)
    # These columns can't be null; a null in the request means "leave it alone".
    for key in ("title", "status", "priority", "description", "acceptance_criteria"):
        if key in data and data[key] is None:
            data.pop(key)
    if "title" in data:
        data["title"] = _clean_title(data["title"])
    if "github_branch" in data:
        data["github_branch"] = normalize_branch(data["github_branch"], story.project.github_repo_url)
    changed = {key: value for key, value in data.items() if getattr(story, key) != value}

    if is_closed(story.sprint):
        # CORE-10: a story in a closed sprint is read-only, except moving an unfinished one out.
        if set(changed) - {"sprint_id"}:
            raise HTTPException(status_code=400, detail=CLOSED_SPRINT)
        if "sprint_id" in changed and story.status == "done":
            raise HTTPException(status_code=400, detail="Done stories stay in the closed sprint where they were finished")
    if "title" in changed:
        ensure_title_available(db, story.project_id, changed["title"], exclude_id=story.id)
    if "assignee_id" in changed:
        ensure_assignee_is_member(db, story.project_id, changed["assignee_id"])

    warnings: list[str] = []
    if "sprint_id" in changed:
        new_sprint_id = changed.pop("sprint_id")
        target = _sprint_in_project(db, new_sprint_id, story.project_id) if new_sprint_id else None
        warnings = move_stories(db, [story], target, user, status_override=changed.pop("status", None))

    old_status, old_points = story.status, story.story_points
    for key, value in changed.items():
        setattr(story, key, value)
    record_change(db, story, "status", old_status, story.status, user.id)
    record_change(db, story, "story_points", old_points, story.story_points, user.id)
    _commit(db)
    return _write_result(db, story, warnings)


@router.post("/stories/{story_id}/subtasks", response_model=StoryWriteResult)
def create_subtask(
    story_id: str,
    payload: StoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StoryWriteResult:
    parent = get_story_for_member(db, story_id, user)
    if parent.parent_story_id:
        raise HTTPException(status_code=400, detail="Subtasks can't have subtasks")
    if is_closed(parent.sprint):
        raise HTTPException(status_code=400, detail=CLOSED_SPRINT)
    title = _clean_title(payload.title)
    ensure_title_available(db, parent.project_id, title)
    ensure_assignee_is_member(db, parent.project_id, payload.assignee_id)
    subtask = Story(
        project_id=parent.project_id,
        sprint_id=parent.sprint_id,
        parent_story_id=parent.id,
        title=title,
        description=payload.description,
        acceptance_criteria=payload.acceptance_criteria,
        status="selected" if parent.sprint_id else "backlog",
        priority=payload.priority,
        story_points=payload.story_points,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        github_branch=normalize_branch(payload.github_branch, parent.project.github_repo_url),
    )
    db.add(subtask)
    db.flush()
    record_creation(db, subtask, user.id)
    _commit(db)
    return _write_result(db, subtask)


@router.delete("/stories/{story_id}", response_model=DeleteResult)
def delete_story(story_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DeleteResult:
    story = get_story_for_member(db, story_id, user)
    batch = soft_delete_story(db, story, user)
    db.commit()
    return DeleteResult(batch_id=batch.id, counts=batch.counts)
