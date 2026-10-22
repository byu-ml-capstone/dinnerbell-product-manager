from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import ensure_member, get_current_user, get_project_for_member
from ..models import DeletionBatch, ProjectMember, User
from ..schemas.trash import RestoreResult, TrashItem
from ..services.soft_delete import restore_batch

router = APIRouter(prefix="/api", tags=["trash"])


def _trash_item(batch: DeletionBatch) -> TrashItem:
    return TrashItem(
        batch_id=batch.id,
        project_id=batch.project_id,
        root_type=batch.root_type,
        root_id=batch.root_id,
        root_label=batch.root_label,
        counts=batch.counts or {},
        deleted_by=batch.deleted_by.name if batch.deleted_by else None,
        deleted_at=batch.deleted_at,
    )


@router.get("/projects/{project_id}/trash", response_model=list[TrashItem])
def project_trash(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TrashItem]:
    project = get_project_for_member(db, project_id, user)
    batches = (
        db.query(DeletionBatch)
        .options(selectinload(DeletionBatch.deleted_by))
        .filter(
            DeletionBatch.project_id == project.id,
            DeletionBatch.restored_at.is_(None),
            DeletionBatch.root_type != "project",
        )
        .order_by(DeletionBatch.deleted_at.desc())
        .all()
    )
    return [_trash_item(batch) for batch in batches]


@router.get("/trash/projects", response_model=list[TrashItem])
def deleted_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TrashItem]:
    member_of = db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user.id)
    batches = (
        db.query(DeletionBatch)
        .options(selectinload(DeletionBatch.deleted_by))
        .filter(
            DeletionBatch.root_type == "project",
            DeletionBatch.restored_at.is_(None),
            DeletionBatch.project_id.in_(member_of),
        )
        .order_by(DeletionBatch.deleted_at.desc())
        .all()
    )
    return [_trash_item(batch) for batch in batches]


@router.post("/trash/{batch_id}/restore", response_model=RestoreResult)
def restore(batch_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> RestoreResult:
    batch = db.get(DeletionBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Deleted item not found")
    # Membership rows survive a project delete, so this works for deleted projects too.
    ensure_member(db, batch.project_id, user)
    restored = restore_batch(db, batch, user)
    db.commit()
    return RestoreResult(batch_id=batch.id, root_type=batch.root_type, root_id=batch.root_id, restored=restored)
