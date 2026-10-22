import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, get_db
from .routers import (
    analyses,
    auth,
    comments,
    dependencies,
    github,
    messages,
    metrics,
    planning,
    projects,
    reviews,
    sprints,
    stories,
    trash,
    users,
)
from .seed import seed_defaults
from .services.jobs import mark_stale_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The schema comes from Alembic (MIG-2); startup only cleans up interrupted jobs and seeds dev data.
    with SessionLocal() as db:
        mark_stale_jobs(db)
        if settings.seed_demo_data:
            seed_defaults(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    users.router,
    projects.router,
    stories.router,
    comments.router,
    dependencies.router,
    sprints.router,
    planning.router,
    metrics.router,
    trash.router,
    github.router,
    analyses.router,
    reviews.router,
    messages.router,
):
    app.include_router(router)


@app.get("/health")
@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unreachable: {exc}") from exc
    return {"ok": True, "service": settings.app_name}
