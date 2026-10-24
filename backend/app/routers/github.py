from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_story_for_member
from ..models import User
from ..schemas.github import StoryGitHubStatus
from ..services.github_client import GitHubClient, get_github_client
from ..services.github_status import lookup_status

router = APIRouter(prefix="/api", tags=["github"])

@router.get("/stories/{story_id}/github", response_model=StoryGitHubStatus)
def story_github_status(
    story_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    github: GitHubClient | None = Depends(get_github_client),
) -> StoryGitHubStatus:
    story = get_story_for_member(db, story_id, user)
    return lookup_status(story.project.github_repo_url, story.github_branch, github)
