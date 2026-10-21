from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_or_404, get_sprint_for_member
from ..models import Sprint, SprintAnalysis, User
from ..schemas.analyses import AnalysisCreate, AnalysisDetail, AnalysisRead, AnalysisSave
from ..services import clock
from ..services.analysis import build_analysis_input, run_analysis
from ..services.llm import AnalysisLLM, require_analysis_llm

router = APIRouter(prefix="/api", tags=["analyses"])

LIST_FIELDS = set(AnalysisRead.model_fields)


def _read(analysis: SprintAnalysis) -> dict:
    data = {field: getattr(analysis, field, None) for field in LIST_FIELDS}
    data["created_by_name"] = analysis.created_by.name if analysis.created_by else None
    data["finalized_by_name"] = analysis.finalized_by.name if analysis.finalized_by else None
    return data


def _analysis_for_member(db: Session, analysis_id: str, user: User) -> SprintAnalysis:
    analysis = get_or_404(db, SprintAnalysis, analysis_id, "Analysis")
    get_sprint_for_member(db, analysis.sprint_id, user)
    return analysis


@router.post("/sprints/{sprint_id}/analyses", response_model=AnalysisRead, status_code=202)
def create_analysis(
    sprint_id: str,
    payload: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    llm: AnalysisLLM = Depends(require_analysis_llm),
) -> AnalysisRead:
    # Works for planned, active and closed sprints (A-9); the AI call runs in the background (AI-11).
    sprint = get_sprint_for_member(db, sprint_id, user)
    snapshot, metrics = build_analysis_input(db, sprint, payload.additional_context.strip())
    analysis = SprintAnalysis(
        sprint_id=sprint.id,
        trigger="manual",
        status="pending",
        model=llm.model,
        additional_context=payload.additional_context.strip(),
        input_snapshot=snapshot,
        metrics=metrics,
        created_by_id=user.id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    background_tasks.add_task(run_analysis, analysis.id, llm)
    return AnalysisRead(**_read(analysis))


@router.get("/sprints/{sprint_id}/analyses", response_model=list[AnalysisRead])
def list_analyses(sprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[AnalysisRead]:
    sprint: Sprint = get_sprint_for_member(db, sprint_id, user)
    analyses = (
        db.query(SprintAnalysis)
        .options(selectinload(SprintAnalysis.created_by), selectinload(SprintAnalysis.finalized_by))
        .filter(SprintAnalysis.sprint_id == sprint.id)
        .order_by(SprintAnalysis.created_at.desc())
        .all()
    )
    return [AnalysisRead(**_read(analysis)) for analysis in analyses]


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> AnalysisDetail:
    analysis = _analysis_for_member(db, analysis_id, user)
    return AnalysisDetail(
        **_read(analysis),
        input_snapshot=analysis.input_snapshot or {},
        metrics=analysis.metrics or {},
        usage=analysis.usage,
    )


@router.put("/analyses/{analysis_id}", response_model=AnalysisRead)
def save_analysis(
    analysis_id: str,
    payload: AnalysisSave,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisRead:
    analysis = _analysis_for_member(db, analysis_id, user)
    if analysis.status != "complete":
        raise HTTPException(status_code=400, detail="Only a completed analysis can be saved")
    analysis.final_content = payload.final_content
    analysis.finalized_at = clock.now()
    analysis.finalized_by_id = user.id
    db.commit()
    db.refresh(analysis)
    return AnalysisRead(**_read(analysis))
