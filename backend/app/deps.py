"""Shared request helpers. Every route reaches its project through one of these (X-9)."""

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Project, ProjectMember, Sprint, SprintMessage, Story, User
from .services.auth import SESSION_COOKIE, user_for_token


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> User:
    user = user_for_token(db, session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user


def get_or_404(db: Session, model, row_id: str, label: str):
    # Session.get can return a cached row without running the filtered query, so check deleted_at too.
    row = db.get(model, row_id)
    if row is None or getattr(row, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return row


def is_member(db: Session, project_id: str, user: User) -> bool:
    return db.query(ProjectMember).filter_by(project_id=project_id, user_id=user.id).first() is not None


def ensure_member(db: Session, project_id: str, user: User) -> None:
    if not is_member(db, project_id, user):
        raise HTTPException(status_code=403, detail="You are not a member of this project")


def get_project_for_member(db: Session, project_id: str, user: User) -> Project:
    project = get_or_404(db, Project, project_id, "Project")
    ensure_member(db, project.id, user)
    return project


def get_sprint_for_member(db: Session, sprint_id: str, user: User) -> Sprint:
    sprint = get_or_404(db, Sprint, sprint_id, "Sprint")
    ensure_member(db, sprint.project_id, user)
    return sprint


def get_story_for_member(db: Session, story_id: str, user: User) -> Story:
    story = get_or_404(db, Story, story_id, "Story")
    ensure_member(db, story.project_id, user)
    return story


def get_message_for_member(db: Session, message_id: str, user: User) -> SprintMessage:
    message = get_or_404(db, SprintMessage, message_id, "Message")
    sprint = get_or_404(db, Sprint, message.sprint_id, "Sprint")
    ensure_member(db, sprint.project_id, user)
    return message
