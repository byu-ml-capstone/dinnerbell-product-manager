"""The only way story events get written (VEL-6). Every status, sprint or points change goes through here."""

from sqlalchemy.orm import Session

from ..models import Story, StoryEvent
from . import clock

FIELD_EVENTS = {
    "status": "status_changed",
    "sprint_id": "sprint_changed",
    "story_points": "points_changed",
}


def _text(value) -> str | None:
    return None if value is None else str(value)


def record_story_event(db: Session, story: Story, event_type: str, from_value, to_value, actor_id: str | None) -> None:
    db.add(
        StoryEvent(
            story_id=story.id,
            project_id=story.project_id,
            event_type=event_type,
            from_value=_text(from_value),
            to_value=_text(to_value),
            actor_id=actor_id,
            created_at=clock.now(),
        )
    )


def record_creation(db: Session, story: Story, actor_id: str | None) -> None:
    """A created event plus one event per tracked field, each going from null to its first value."""
    if story.id is None:
        db.flush()
    record_story_event(db, story, "created", None, None, actor_id)
    record_story_event(db, story, "status_changed", None, story.status, actor_id)
    if story.sprint_id:
        record_story_event(db, story, "sprint_changed", None, story.sprint_id, actor_id)
    if story.story_points:
        record_story_event(db, story, "points_changed", None, story.story_points, actor_id)


def record_change(db: Session, story: Story, field: str, old, new, actor_id: str | None) -> None:
    if old == new:
        return
    record_story_event(db, story, FIELD_EVENTS[field], old, new, actor_id)
