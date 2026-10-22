from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_or_404, get_project_for_member, get_sprint_for_member
from ..models import Sprint, SprintAnalysis, Story, User
from ..schemas.sprints import MoveUnfinishedRequest, SprintClose, SprintCloseResult, SprintCreate, SprintRead, SprintUpdate
from ..schemas.stories import MoveUnfinishedResult
from ..schemas.trash import DeleteResult
from ..services import clock
from ..services.analysis import build_analysis_input, run_analysis
from ..services.llm import AnalysisLLM, get_analysis_llm
from ..services.metrics import sprint_metrics
from ..services.moves import move_stories, unfinished_top_level
from ..services.soft_delete import delete_sprint as soft_delete_sprint
from ..services.sprints import is_closed, serialize_sprint, serialize_sprints
from ..services.stories import backlog_order, story_summaries, summary_options

router = APIRouter(prefix="/api", tags=["sprints"])

STATUSES = ["backlog", "selected", "in_progress", "blocked", "done"]


@router.post("/projects/{project_id}/sprints", response_model=SprintRead)
def create_sprint(
    project_id: str,
    payload: SprintCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SprintRead:
    project = get_project_for_member(db, project_id, user)
    # Any number of sprints can be active at once (CORE-8); status comes from the dates (CORE-13).
    count = db.query(Sprint).execution_options(include_deleted=True).filter(Sprint.project_id == project.id).count()
    sprint = Sprint(
        project_id=project.id,
        name=(payload.name or "").strip() or f"Sprint {count + 1}",
        goal=payload.goal,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return serialize_sprint(db, sprint)


@router.get("/projects/{project_id}/sprints", response_model=list[SprintRead])
def list_sprints(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SprintRead]:
    project = get_project_for_member(db, project_id, user)
    sprints = (
        db.query(Sprint)
        .filter(Sprint.project_id == project.id)
        .order_by(Sprint.start_date.desc(), Sprint.created_at.desc())
        .all()
    )
    return serialize_sprints(db, sprints)


@router.get("/sprints/{sprint_id}", response_model=SprintRead)
def get_sprint(sprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> SprintRead:
    return serialize_sprint(db, get_sprint_for_member(db, sprint_id, user))


@router.put("/sprints/{sprint_id}", response_model=SprintRead)
def update_sprint(
    sprint_id: str,
    payload: SprintUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SprintRead:
    sprint = get_sprint_for_member(db, sprint_id, user)
    if is_closed(sprint):
        raise HTTPException(status_code=400, detail="Sprint is closed")
    data = {key: value for key, value in payload.model_dump(exclude_unset=True).items() if value is not None}
    start = data.get("start_date", sprint.start_date)
    end = data.get("end_date", sprint.end_date)
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if "name" in data:
        data["name"] = data["name"].strip()
    for key, value in data.items():
        setattr(sprint, key, value)
    db.commit()
    db.refresh(sprint)
    return serialize_sprint(db, sprint)


@router.delete("/sprints/{sprint_id}", response_model=DeleteResult)
def delete_sprint(sprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DeleteResult:
    sprint = get_sprint_for_member(db, sprint_id, user)
    batch = soft_delete_sprint(db, sprint, user)
    db.commit()
    return DeleteResult(batch_id=batch.id, counts=batch.counts)


@router.get("/sprints/{sprint_id}/board")
def get_board(sprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    sprint = get_sprint_for_member(db, sprint_id, user)
    # The sprint's own stories plus this project's backlog, never another project's (BUG-1).
    stories = (
        db.query(Story)
        .options(*summary_options())
        .filter(
            or_(
                Story.sprint_id == sprint.id,
                and_(Story.project_id == sprint.project_id, Story.sprint_id.is_(None)),
            )
        )
        .all()
    )
    columns: dict[str, list] = {status: [] for status in STATUSES}
    for summary in story_summaries(db, sorted(stories, key=backlog_order)):
        column = "backlog" if summary.sprint_id is None else summary.status
        columns[column].append(summary.model_dump(mode="json"))
    return {"sprint_id": sprint.id, "read_only": is_closed(sprint), "columns": columns}


@router.post("/sprints/{sprint_id}/close", response_model=SprintCloseResult)
def close_sprint(
    sprint_id: str,
    payload: SprintClose,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    llm: AnalysisLLM | None = Depends(get_analysis_llm),
) -> SprintCloseResult:
    sprint = get_sprint_for_member(db, sprint_id, user)
    if is_closed(sprint):
        raise HTTPException(status_code=400, detail="Sprint is already closed")
    committed = sprint_metrics(db, sprint).committed_points
    stories = db.query(Story).filter(Story.sprint_id == sprint.id, Story.parent_story_id.is_(None)).all()
    done = [story for story in stories if story.status == "done"]
    # Velocity is always points; unpointed stories count as 0 (VEL-1, BUG-10).
    sprint.velocity = sum(story.story_points or 0 for story in done)
    sprint.committed_points = committed
    sprint.closed_at = clock.now()
    sprint.closed_by_id = user.id
    sprint.notes = payload.notes
    db.commit()

    analysis_id = None
    if llm is not None:
        # D-33: every close starts an analysis; a failed analysis never undoes the close.
        snapshot, metrics = build_analysis_input(db, sprint, "")
        analysis = SprintAnalysis(
            sprint_id=sprint.id,
            trigger="sprint_closed",
            status="pending",
            model=llm.model,
            input_snapshot=snapshot,
            metrics=metrics,
            created_by_id=None,
        )
        db.add(analysis)
        db.commit()
        analysis_id = analysis.id
        background_tasks.add_task(run_analysis, analysis.id, llm)

    return SprintCloseResult(
        id=sprint.id,
        status="closed",
        closed_at=sprint.closed_at,
        velocity=sprint.velocity,
        committed_points=sprint.committed_points,
        completed_stories=len(done),
        incomplete_stories=len(stories) - len(done),
        unpointed_done_stories=sum(1 for story in done if not story.story_points),
        analysis_id=analysis_id,
    )


@router.post("/sprints/{sprint_id}/move-unfinished", response_model=MoveUnfinishedResult)
def move_unfinished(
    sprint_id: str,
    payload: MoveUnfinishedRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MoveUnfinishedResult:
    sprint = get_sprint_for_member(db, sprint_id, user)
    target = None
    if payload.target_sprint_id:
        target = get_or_404(db, Sprint, payload.target_sprint_id, "Sprint")
        if target.project_id != sprint.project_id:
            raise HTTPException(status_code=404, detail="Sprint not found")
        if target.id == sprint.id:
            raise HTTPException(status_code=400, detail="Pick a different sprint")
    stories = unfinished_top_level(db, sprint)
    warnings = move_stories(db, stories, target, user)
    db.commit()
    return MoveUnfinishedResult(moved=len(stories), warnings=warnings)
