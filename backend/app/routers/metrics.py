from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_project_for_member, get_sprint_for_member
from ..models import User
from ..schemas.metrics import SprintMetrics, VelocityRead
from ..services.metrics import sprint_metrics, velocity_history

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/projects/{project_id}/velocity", response_model=VelocityRead)
def project_velocity(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> VelocityRead:
    project = get_project_for_member(db, project_id, user)
    return velocity_history(db, project.id)


@router.get("/sprints/{sprint_id}/metrics", response_model=SprintMetrics)
def get_sprint_metrics(sprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SprintMetrics:
    return sprint_metrics(db, get_sprint_for_member(db, sprint_id, user))
