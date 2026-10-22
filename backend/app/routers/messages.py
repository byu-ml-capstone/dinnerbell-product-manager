from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, get_message_for_member, get_or_404, get_sprint_for_member
from ..models import Sprint, SprintMessage, User
from ..schemas.messages import MessageCreate, MessageRead, MessageUpdate
from ..schemas.trash import DeleteResult
from ..services import clock
from ..services.soft_delete import delete_message as soft_delete_message

router = APIRouter(prefix="/api", tags=["messages"])


def _read(message: SprintMessage, replies: list[SprintMessage] | None = None) -> MessageRead:
    return MessageRead(
        id=message.id,
        sprint_id=message.sprint_id,
        author_id=message.author_id,
        author_name=message.author.name,
        parent_message_id=message.parent_message_id,
        text=message.text,
        created_at=message.created_at,
        edited_at=message.edited_at,
        replies=[_read(reply) for reply in replies or []],
    )


def _own_message(db: Session, message_id: str, user: User) -> SprintMessage:
    message = get_message_for_member(db, message_id, user)
    if message.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can change this message")
    return message


@router.get("/sprints/{sprint_id}/messages", response_model=list[MessageRead])
def list_messages(
    sprint_id: str,
    since: datetime | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageRead]:
    sprint = get_sprint_for_member(db, sprint_id, user)
    query = db.query(SprintMessage).options(selectinload(SprintMessage.author)).filter(SprintMessage.sprint_id == sprint.id)
    if since is not None:
        # Polling (CHAT-5): a flat list of anything created or edited after `since`.
        changed = (
            query.filter(or_(SprintMessage.created_at > since, SprintMessage.edited_at > since))
            .order_by(SprintMessage.created_at)
            .all()
        )
        return [_read(message) for message in changed]
    messages = query.order_by(SprintMessage.created_at).all()
    replies: dict[str, list[SprintMessage]] = {}
    for message in messages:
        if message.parent_message_id:
            replies.setdefault(message.parent_message_id, []).append(message)
    posts = [message for message in messages if not message.parent_message_id]
    return [_read(post, replies.get(post.id)) for post in reversed(posts)]


@router.post("/sprints/{sprint_id}/messages", response_model=MessageRead, status_code=201)
def create_message(
    sprint_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageRead:
    sprint = get_sprint_for_member(db, sprint_id, user)
    if payload.parent_message_id:
        parent = get_or_404(db, SprintMessage, payload.parent_message_id, "Message")
        if parent.sprint_id != sprint.id:
            raise HTTPException(status_code=400, detail="That post belongs to another sprint")
        if parent.parent_message_id:
            raise HTTPException(status_code=400, detail="You can only reply to a top-level post")
    message = SprintMessage(sprint_id=sprint.id, author_id=user.id, parent_message_id=payload.parent_message_id, text=payload.text)
    db.add(message)
    db.commit()
    db.refresh(message)
    return _read(message)


@router.put("/sprint-messages/{message_id}", response_model=MessageRead)
def update_message(
    message_id: str,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageRead:
    message = _own_message(db, message_id, user)
    message.text = payload.text
    message.edited_at = clock.now()
    db.commit()
    db.refresh(message)
    return _read(message)


@router.delete("/sprint-messages/{message_id}", response_model=DeleteResult)
def delete_message(message_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DeleteResult:
    message = _own_message(db, message_id, user)
    sprint: Sprint = get_or_404(db, Sprint, message.sprint_id, "Sprint")
    batch = soft_delete_message(db, message, sprint, user)
    db.commit()
    return DeleteResult(batch_id=batch.id, counts=batch.counts)
