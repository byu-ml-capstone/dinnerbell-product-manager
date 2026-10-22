from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_story_for_member
from ..models import Comment, User
from ..schemas.stories import CommentCreate, CommentRead
from ..services.stories import comment_read

router = APIRouter(prefix="/api", tags=["comments"])


@router.post("/stories/{story_id}/comments", response_model=CommentRead)
def create_comment(
    story_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CommentRead:
    # Comments stay open on every story, including ones in closed sprints (CORE-10).
    story = get_story_for_member(db, story_id, user)
    comment = Comment(story_id=story.id, author_id=user.id, text=payload.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_read(comment)
