from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas.auth import LoginRequest, RegisterRequest, UserRead
from ..services.auth import SESSION_COOKIE, create_session, delete_session, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> User:
    username = payload.username.lower()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="That username is taken")
    user = User(username=username, name=payload.name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is taken") from exc
    token = create_session(db, user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserRead)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.username == payload.username.strip().lower()).first()
    if not user or not verify_password(user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(db, user)
    db.commit()
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> Response:
    delete_session(db, session_token)
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
