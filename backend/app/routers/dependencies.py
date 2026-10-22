from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_project_for_member, get_story_for_member
from ..models import Dependency, Story, User
from ..schemas.graph import DependencyGraph
from ..schemas.stories import DependencyCreate, DependencyWriteResult
from ..schemas.trash import DeleteResult
from ..services.graph import build_graph, find_cycle, order_warning, order_warning_message
from ..services.soft_delete import delete_dependency as soft_delete_dependency
from ..services.stories import dependency_read

router = APIRouter(prefix="/api", tags=["dependencies"])


@router.post("/stories/{story_id}/blocks/{target_story_id}", response_model=DependencyWriteResult)
def create_dependency(
    story_id: str,
    target_story_id: str,
    payload: DependencyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DependencyWriteResult:
    blocker = get_story_for_member(db, story_id, user)
    blocked = get_story_for_member(db, target_story_id, user)
    if blocker.id == blocked.id:
        raise HTTPException(status_code=400, detail="A story cannot block itself")
    if blocker.project_id != blocked.project_id:
        raise HTTPException(status_code=400, detail="Stories are in different projects")
    if db.query(Dependency).filter_by(blocker_story_id=blocker.id, blocked_story_id=blocked.id).first():
        raise HTTPException(status_code=409, detail="These stories are already linked")
    cycle = find_cycle(db, blocker.project_id, blocker.id, blocked.id)
    if cycle:
        titles = {story.id: story.title for story in db.query(Story).filter(Story.id.in_(set(cycle)))}
        raise HTTPException(status_code=400, detail="This would create a cycle: " + " → ".join(titles[item] for item in cycle))

    # Adding a link never changes either story's status; blocked is set by hand (D-20, BUG-3).
    link = Dependency(blocker_story_id=blocker.id, blocked_story_id=blocked.id, reason=payload.reason.strip())
    db.add(link)
    db.commit()
    db.refresh(link)
    warnings = [order_warning_message(blocker, blocked)] if order_warning(blocker, blocked) else []
    return DependencyWriteResult(**dependency_read(link).model_dump(), warnings=warnings)


@router.delete("/stories/{story_id}/blocks/{target_story_id}", response_model=DeleteResult)
def delete_dependency(
    story_id: str,
    target_story_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeleteResult:
    blocker = get_story_for_member(db, story_id, user)
    blocked = get_story_for_member(db, target_story_id, user)
    link = db.query(Dependency).filter_by(blocker_story_id=blocker.id, blocked_story_id=blocked.id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Blocking relationship not found")
    batch = soft_delete_dependency(db, link, user)
    db.commit()
    return DeleteResult(batch_id=batch.id, counts=batch.counts)


@router.get("/projects/{project_id}/dependency-graph", response_model=DependencyGraph)
def dependency_graph(
    project_id: str,
    sprint_id: str | None = Query(default=None, description='A sprint id, "backlog", or omit for all'),
    include_done: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DependencyGraph:
    project = get_project_for_member(db, project_id, user)
    return build_graph(db, project.id, sprint_id, include_done)
