"""Velocity, committed points and burndown, rebuilt by replaying story_events (VEL-4 to VEL-9).

Only top-level stories count (VEL-2); unpointed stories count as 0 (VEL-1).
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Sprint, Story, StoryEvent
from ..schemas.metrics import BurndownPoint, SprintMetrics, VelocityRead, VelocitySprint
from . import clock
from .sprints import is_closed


@dataclass
class _State:
    status: str | None = None
    sprint_id: str | None = None
    points: int = 0
    deleted: bool = False


def _apply(state: _State, event: StoryEvent) -> None:
    if event.event_type == "status_changed":
        state.status = event.to_value
    elif event.event_type == "sprint_changed":
        state.sprint_id = event.to_value
    elif event.event_type == "points_changed":
        state.points = int(event.to_value) if event.to_value else 0
    elif event.event_type == "deleted":
        state.deleted = True
    elif event.event_type == "restored":
        state.deleted = False


def closed_sprints(db: Session, project_id: str, exclude_id: str | None = None, limit: int | None = None) -> list[Sprint]:
    """Closed, non-deleted sprints, most recently closed first."""
    query = db.query(Sprint).filter(Sprint.project_id == project_id, Sprint.closed_at.is_not(None))
    if exclude_id:
        query = query.filter(Sprint.id != exclude_id)
    query = query.order_by(Sprint.closed_at.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def average_velocity(db: Session, project_id: str, exclude_id: str | None = None) -> float | None:
    """Average of the last 3 closed sprints (VEL-8)."""
    recent = closed_sprints(db, project_id, exclude_id, limit=3)
    if not recent:
        return None
    return sum(sprint.velocity or 0 for sprint in recent) / len(recent)


def historical_points_per_day(db: Session, project_id: str, exclude_id: str | None = None) -> float | None:
    recent = closed_sprints(db, project_id, exclude_id, limit=3)
    if not recent:
        return None
    rates = [(sprint.velocity or 0) / ((sprint.end_date - sprint.start_date).days + 1) for sprint in recent]
    return sum(rates) / len(rates)


def velocity_history(db: Session, project_id: str) -> VelocityRead:
    sprints = list(reversed(closed_sprints(db, project_id, limit=6)))
    average = average_velocity(db, project_id)
    return VelocityRead(
        sprints=[
            VelocitySprint(
                id=sprint.id,
                name=sprint.name,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                committed_points=sprint.committed_points,
                velocity=sprint.velocity or 0,
                closed_at=sprint.closed_at,
            )
            for sprint in sprints
        ],
        average_velocity_3=round(average, 2) if average is not None else None,
    )


def capacity_warning(planned_points: int, average: float | None) -> str | None:
    if average is None or planned_points <= average:
        return None
    return f"⚠ {planned_points} pts planned vs {round(average, 1):g} avg velocity"


def _top_level_now(db: Session, sprint: Sprint) -> list[Story]:
    return db.query(Story).filter(Story.sprint_id == sprint.id, Story.parent_story_id.is_(None)).all()


def _burndown_events(db: Session, sprint: Sprint, current_ids: set[str]) -> list[StoryEvent]:
    touched = {
        story_id
        for (story_id,) in db.query(StoryEvent.story_id).filter(
            StoryEvent.event_type == "sprint_changed",
            or_(StoryEvent.from_value == sprint.id, StoryEvent.to_value == sprint.id),
        )
    }
    candidate_ids = touched | current_ids
    if not candidate_ids:
        return []
    top_level_ids = {
        story_id
        for (story_id,) in db.query(Story.id)
        .execution_options(include_deleted=True)
        .filter(Story.id.in_(candidate_ids), Story.parent_story_id.is_(None))
    }
    if not top_level_ids:
        return []
    return (
        db.query(StoryEvent)
        .filter(StoryEvent.story_id.in_(top_level_ids))
        .order_by(StoryEvent.created_at)
        .all()
    )


def sprint_metrics(db: Session, sprint: Sprint) -> SprintMetrics:
    today = clock.today()
    closed = is_closed(sprint)
    current = _top_level_now(db, sprint)
    completed = sum(story.story_points or 0 for story in current if story.status == "done")
    remaining = sum(story.story_points or 0 for story in current if story.status != "done")
    unpointed_done = sum(1 for story in current if story.status == "done" and not story.story_points)

    # A closed sprint shows how things stood when it closed, so stories carried out afterwards
    # don't look like removed scope (D-28).
    cutoff = sprint.closed_at if closed else None
    last_day = min(today, sprint.end_date)
    if closed:
        last_day = min(last_day, clock.local_date(sprint.closed_at))

    events = _burndown_events(db, sprint, {story.id for story in current})
    states: dict[str, _State] = {}
    position = 0

    def advance(until) -> None:
        nonlocal position
        while position < len(events) and events[position].created_at < until:
            event = events[position]
            _apply(states.setdefault(event.story_id, _State()), event)
            position += 1

    def in_sprint() -> dict[str, _State]:
        return {story_id: state for story_id, state in states.items() if state.sprint_id == sprint.id and not state.deleted}

    committed: int | None = None
    burndown: list[BurndownPoint] = []
    scope_added = scope_removed = 0
    total_days = (sprint.end_date - sprint.start_date).days
    previous: dict[str, _State] = {}
    previous_points: dict[str, int] = {}
    day: date = sprint.start_date
    while day <= last_day:
        advance(min(clock.end_of_day(day), cutoff) if cutoff else clock.end_of_day(day))
        members = in_sprint()
        points_now = {story_id: state.points for story_id, state in members.items()}
        change = 0
        if day == sprint.start_date:
            committed = sum(points_now.values())
        else:
            added = sum(points_now[story_id] for story_id in members.keys() - previous.keys())
            removed = sum(previous_points[story_id] for story_id in previous.keys() - members.keys())
            scope_added += added
            scope_removed += removed
            change = added - removed
        ideal = (committed or 0) * (sprint.end_date - day).days / total_days if total_days > 0 else 0.0
        burndown.append(
            BurndownPoint(
                date=day,
                remaining_points=sum(state.points for state in members.values() if state.status != "done"),
                ideal_points=round(ideal, 2),
                scope_change_points=change,
            )
        )
        previous, previous_points = members, points_now
        day += timedelta(days=1)

    if closed:
        advance(cutoff)
        at_close = in_sprint().values()
        completed = sum(state.points for state in at_close if state.status == "done")
        remaining = sum(state.points for state in at_close if state.status != "done")
        unpointed_done = sum(1 for state in at_close if state.status == "done" and not state.points)

    if today < sprint.start_date:
        days_elapsed = 0
        days_remaining = total_days + 1
    else:
        days_elapsed = (min(today, sprint.end_date) - sprint.start_date).days + 1
        days_remaining = 0 if is_closed(sprint) else max(0, (sprint.end_date - today).days)

    points_per_day = historical_points_per_day(db, sprint.project_id, exclude_id=sprint.id)
    if points_per_day is None and completed > 0 and days_elapsed > 0:
        points_per_day = completed / days_elapsed
    estimate = None
    if points_per_day and not closed:
        estimate = today + timedelta(days=math.ceil(remaining / points_per_day))

    total = completed + remaining
    return SprintMetrics(
        committed_points=committed,
        completed_points=completed,
        remaining_points=remaining,
        percent_complete=round(completed / total * 100, 1) if total else None,
        scope_added_points=scope_added,
        scope_removed_points=scope_removed,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        unpointed_story_count=unpointed_done,
        points_per_day=round(points_per_day, 2) if points_per_day else None,
        estimated_completion_date=estimate,
        burndown=burndown,
    )
