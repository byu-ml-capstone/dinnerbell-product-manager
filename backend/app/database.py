from collections.abc import Generator
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker, with_loader_criteria

from .config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class SoftDeleteMixin:
    """Rows are never hard-deleted (D-26); they are hidden by the global filter below."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    deletion_batch_id: Mapped[str | None] = mapped_column(ForeignKey("deletion_batches.id"), nullable=True)


@event.listens_for(Session, "do_orm_execute")
def _hide_deleted_rows(execute_state) -> None:
    # DEL-10: every ORM SELECT (including relationship lazy loads) leaves out soft-deleted rows
    # unless the caller opts in with .execution_options(include_deleted=True) (Trash and restore only).
    # Column refreshes are skipped so a row that was just soft-deleted can still be read back.
    if (
        execute_state.is_select
        and not execute_state.is_column_load
        and not execute_state.execution_options.get("include_deleted", False)
    ):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(SoftDeleteMixin, lambda cls: cls.deleted_at.is_(None), include_aliases=True)
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
