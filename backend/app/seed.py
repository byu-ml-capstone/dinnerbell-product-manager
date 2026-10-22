"""Demo data for local development only. Runs when SEED_DEMO_DATA=true, never on staging or prod (AUTH-5)."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Project, ProjectMember, Sprint, Story, StoryEvent, User
from .services import clock
from .services.auth import hash_password
from .services.events import record_creation

DEMO_PASSWORD = "devpassword"
DEMO_USERS = [
    ("taylor", "Taylor Lead"),
    ("jordan", "Jordan Dev"),
    ("casey", "Casey QA"),
    ("morgan", "Morgan PM"),
]


def _story(db: Session, actor: User, when: datetime, **fields) -> Story:
    story = Story(**fields)
    db.add(story)
    db.flush()
    record_creation(db, story, actor.id)
    db.flush()
    # Backdate the creation events so the demo burndown and velocity look like real history.
    db.query(StoryEvent).filter(StoryEvent.story_id == story.id).update({"created_at": when})
    return story


def _finish(db: Session, story: Story, actor: User, when: datetime) -> None:
    db.add(
        StoryEvent(
            story_id=story.id,
            project_id=story.project_id,
            event_type="status_changed",
            from_value=story.status,
            to_value="done",
            actor_id=actor.id,
            created_at=when,
        )
    )
    story.status = "done"


def seed_defaults(db: Session) -> None:
    if db.query(Project).execution_options(include_deleted=True).count() > 0:
        return

    users = {}
    for username, name in DEMO_USERS:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            user = User(username=username, name=name, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
        users[username] = user
    db.flush()
    lead = users["taylor"]

    project = Project(
        name="DinnerBell Demo",
        description="Demo project seeded for local development.",
        owner_id=lead.id,
    )
    db.add(project)
    db.flush()
    for user in users.values():
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role="member"))

    today = clock.today()
    closed = Sprint(
        project_id=project.id,
        name="Sprint 1",
        goal="Recipe search and the first planner screens.",
        start_date=today - timedelta(days=21),
        end_date=today - timedelta(days=8),
    )
    active = Sprint(
        project_id=project.id,
        name="Sprint 2",
        goal="Weekly meal plan and grocery list.",
        start_date=today - timedelta(days=6),
        end_date=today + timedelta(days=7),
    )
    planned = Sprint(
        project_id=project.id,
        name="Sprint 3",
        goal="Sharing plans with family members.",
        start_date=today + timedelta(days=8),
        end_date=today + timedelta(days=21),
    )
    db.add_all([closed, active, planned])
    db.flush()

    def at(day, hour=9):
        return clock.start_of_day(day) + timedelta(hours=hour)

    # Sprint 1 (closed): two done, one carried over below.
    s1a = _story(db, lead, at(closed.start_date), project_id=project.id, sprint_id=closed.id, title="Recipe search API",
                 status="in_progress", priority="high", story_points=5, assignee_id=users["jordan"].id,
                 acceptance_criteria="Search by ingredient and by name.")
    s1b = _story(db, lead, at(closed.start_date), project_id=project.id, sprint_id=closed.id, title="Recipe card UI",
                 status="in_progress", priority="medium", story_points=3, assignee_id=users["taylor"].id)
    _finish(db, s1a, users["jordan"], at(closed.start_date + timedelta(days=6)))
    _finish(db, s1b, users["taylor"], at(closed.start_date + timedelta(days=10)))
    closed.velocity = 8
    closed.committed_points = 16
    closed.closed_at = at(closed.end_date, 17)
    closed.closed_by_id = lead.id

    # Sprint 2 (active).
    plan = _story(db, lead, at(closed.start_date), project_id=project.id, sprint_id=closed.id, title="Weekly meal plan view",
                  status="in_progress", priority="urgent", story_points=8, assignee_id=users["taylor"].id,
                  description="A seven-day grid of planned meals.",
                  acceptance_criteria="Shows seven days.\nMeals can be dragged between days.")
    # Carried over from Sprint 1 into Sprint 2.
    db.add(StoryEvent(story_id=plan.id, project_id=project.id, event_type="sprint_changed", from_value=closed.id,
                      to_value=active.id, actor_id=lead.id, created_at=at(closed.end_date, 16)))
    plan.sprint_id = active.id
    grocery = _story(db, lead, at(active.start_date), project_id=project.id, sprint_id=active.id, title="Grocery list from plan",
                     status="in_progress", priority="high", story_points=5, assignee_id=users["jordan"].id,
                     acceptance_criteria="Combines ingredients from every planned meal.")
    login = _story(db, lead, at(active.start_date), project_id=project.id, sprint_id=active.id, title="Family login",
                   status="selected", priority="medium", story_points=3, assignee_id=users["casey"].id)
    _story(db, lead, at(active.start_date), project_id=project.id, sprint_id=active.id, title="Pantry tracking",
           status="blocked", priority="low", story_points=2, assignee_id=users["morgan"].id)
    _finish(db, login, users["casey"], at(active.start_date + timedelta(days=3)))
    _story(db, lead, at(active.start_date), project_id=project.id, sprint_id=active.id, parent_story_id=grocery.id,
           title="Grocery list: write tests", status="selected", priority="medium", assignee_id=users["casey"].id)

    # Sprint 3 (planned) and the backlog.
    _story(db, lead, at(today), project_id=project.id, sprint_id=planned.id, title="Share plan with family",
           status="selected", priority="medium", story_points=5)
    _story(db, lead, at(today), project_id=project.id, title="Nutrition summary", status="backlog", priority="low",
           story_points=8)
    db.commit()
