from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas.auth import UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[User]:
    # Requires login and leaves out email (BUG-14).
    return db.query(User).order_by(User.name).all()
