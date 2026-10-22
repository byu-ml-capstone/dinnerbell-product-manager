from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_or_404, get_sprint_for_member
from ..models import SprintReview, Story, User
from ..schemas.reviews import ReviewDetail, ReviewRead
from ..services.github_client import GitHubClient, get_github_client
from ..services.jobs import ACTIVE_STATUSES
from ..services.llm import ReviewLLM, get_review_llm
from ..services.sprint_review import run_review

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/sprints/{sprint_id}/reviews", response_model=ReviewRead, status_code=202)
def start_review(
    sprint_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    llm: ReviewLLM | None = Depends(get_review_llm),
    github: GitHubClient | None = Depends(get_github_client),
) -> SprintReview:
    sprint = get_sprint_for_member(db, sprint_id, user)
    repo_url = sprint.project.github_repo_url
    if not repo_url:
        raise HTTPException(status_code=400, detail="Set the project's GitHub repository in Settings first")
    if github is None:
        raise HTTPException(status_code=503, detail="GitHub token not configured. Set GITHUB_TOKEN.")
    if llm is None:
        raise HTTPException(status_code=503, detail="Sprint review isn't configured. Set REVIEW_LLM_API_KEY and REVIEW_LLM_MODEL.")
    running = db.query(SprintReview).filter(SprintReview.sprint_id == sprint.id, SprintReview.status.in_(ACTIVE_STATUSES)).first()
    if running:
        raise HTTPException(status_code=409, detail="A sprint review is already running for this sprint")
    review = SprintReview(sprint_id=sprint.id, status="pending", model=llm.model, repo_url=repo_url, created_by_id=user.id)
    db.add(review)
    db.commit()
    db.refresh(review)
    background_tasks.add_task(run_review, review.id, llm, github)
    return review


@router.get("/sprints/{sprint_id}/reviews", response_model=list[ReviewRead])
def list_reviews(sprint_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SprintReview]:
    sprint = get_sprint_for_member(db, sprint_id, user)
    return db.query(SprintReview).filter(SprintReview.sprint_id == sprint.id).order_by(SprintReview.created_at.desc()).all()


@router.get("/reviews/{review_id}", response_model=ReviewDetail)
def get_review(review_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ReviewDetail:
    review = get_or_404(db, SprintReview, review_id, "Review")
    get_sprint_for_member(db, review.sprint_id, user)
    review = db.query(SprintReview).options(selectinload(SprintReview.items)).filter(SprintReview.id == review.id).one()
    # Items stay as history, but deleted stories are left out of the UI (X-3).
    story_ids = {item.story_id for item in review.items}
    active = {story_id for (story_id,) in db.query(Story.id).filter(Story.id.in_(story_ids))} if story_ids else set()
    detail = ReviewDetail.model_validate(review)
    detail.items = [item for item in detail.items if item.story_id in active]
    return detail
