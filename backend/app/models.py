import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, SoftDeleteMixin

FIBONACCI_POINTS = (1, 2, 3, 5, 8, 13)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("user"))
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("sess"))
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship()


class DeletionBatch(Base):
    """One delete action and everything deleted with it (DEL-9). Restore undoes a whole batch."""

    __tablename__ = "deletion_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("batch"))
    # Not a foreign key: projects also point at this table, and the project row may itself be in the batch.
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    root_type: Mapped[str] = mapped_column(String(32), nullable=False)
    root_id: Mapped[str] = mapped_column(String(64), nullable=False)
    root_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    deleted_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    restored_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deleted_by: Mapped[User | None] = relationship(foreign_keys=[deleted_by_id])


class Project(SoftDeleteMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("proj"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    github_repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project")
    stories: Mapped[list["Story"]] = relationship(back_populates="project")
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("member"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Kept for history; always "member" because there is one role (PERM-1).
    role: Mapped[str] = mapped_column(String(64), default="member")

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Sprint(SoftDeleteMixin, Base):
    __tablename__ = "sprints"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_sprints_dates"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("sprint"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Completed points of top-level stories, set once at close (VEL-1, VEL-10).
    velocity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    committed_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="sprints")
    stories: Mapped[list["Story"]] = relationship(back_populates="sprint")


class Story(SoftDeleteMixin, Base):
    __tablename__ = "stories"
    __table_args__ = (
        CheckConstraint("story_points IS NULL OR story_points IN (1, 2, 3, 5, 8, 13)", name="ck_stories_points"),
        Index(
            "uq_stories_project_title_active",
            "project_id",
            text("lower(title)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("story"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    sprint_id: Mapped[str | None] = mapped_column(ForeignKey("sprints.id"), nullable=True, index=True)
    parent_story_id: Mapped[str | None] = mapped_column(ForeignKey("stories.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="backlog")
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    github_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="stories")
    sprint: Mapped[Sprint | None] = relationship(back_populates="stories")
    parent: Mapped["Story | None"] = relationship(remote_side=[id], back_populates="subtasks")
    subtasks: Mapped[list["Story"]] = relationship(back_populates="parent", order_by="Story.created_at")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    comments: Mapped[list["Comment"]] = relationship(back_populates="story", order_by="Comment.created_at")
    blocks: Mapped[list["Dependency"]] = relationship(foreign_keys="Dependency.blocker_story_id", back_populates="blocker")
    blocked_by_links: Mapped[list["Dependency"]] = relationship(
        foreign_keys="Dependency.blocked_story_id",
        back_populates="blocked",
    )


class Dependency(SoftDeleteMixin, Base):
    __tablename__ = "dependencies"
    __table_args__ = (
        Index(
            "uq_dependency_pair_active",
            "blocker_story_id",
            "blocked_story_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("block"))
    blocker_story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False)
    blocked_story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    blocker: Mapped[Story] = relationship(foreign_keys=[blocker_story_id], back_populates="blocks")
    blocked: Mapped[Story] = relationship(foreign_keys=[blocked_story_id], back_populates="blocked_by_links")


class Comment(SoftDeleteMixin, Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("comment"))
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    story: Mapped[Story] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(foreign_keys=[author_id])


class StoryEvent(Base):
    """Every change to a story's status, sprint or points (VEL-6). Burndown and history replay these."""

    __tablename__ = "story_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evt"))
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    actor: Mapped[User | None] = relationship()


class SprintAnalysis(Base):
    __tablename__ = "sprint_analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("analysis"))
    sprint_id: Mapped[str] = mapped_column(ForeignKey("sprints.id"), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    additional_context: Mapped[str] = mapped_column(Text, default="")
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])
    finalized_by: Mapped[User | None] = relationship(foreign_keys=[finalized_by_id])


class SprintReview(Base):
    __tablename__ = "sprint_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("review"))
    sprint_id: Mapped[str] = mapped_column(ForeignKey("sprints.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    repo_url: Mapped[str] = mapped_column(String(512), nullable=False)
    items_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    unlinked_work: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    usage: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])
    items: Mapped[list["SprintReviewItem"]] = relationship(back_populates="review", order_by="SprintReviewItem.created_at")


class SprintReviewItem(Base):
    __tablename__ = "sprint_review_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rvitem"))
    review_id: Mapped[str] = mapped_column(ForeignKey("sprint_reviews.id"), nullable=False, index=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"), nullable=False, index=True)
    story_title: Mapped[str] = mapped_column(String(255), nullable=False)
    claimed_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    criteria: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    has_tests: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    head_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    reused_from_item_id: Mapped[str | None] = mapped_column(ForeignKey("sprint_review_items.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    review: Mapped[SprintReview] = relationship(back_populates="items")


class SprintMessage(SoftDeleteMixin, Base):
    __tablename__ = "sprint_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg"))
    sprint_id: Mapped[str] = mapped_column(ForeignKey("sprints.id"), nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_message_id: Mapped[str | None] = mapped_column(ForeignKey("sprint_messages.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    author: Mapped[User] = relationship(foreign_keys=[author_id])
