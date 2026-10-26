"""Local-only PR UI fixtures, excluded from the production backend image

Run through compose.github-ui-demo.yaml on a separate database
All GitHub responses come from FakeGitHub; no GitHub token or network is used
"""

from contextlib import asynccontextmanager

import uvicorn

from app.database import SessionLocal
from app.main import app
from app.models import Project, ProjectMember, Story, User
from app.services.github_client import get_github_client

from .fakes import FakeGitHub

github = FakeGitHub()
github.pulls["alice/closed"] = [{
    "number": 22,
    "title": "Closed without merging (mock)",
    "state": "closed",
    "merged_at": None,
    "created_at": "2026-10-20T00:00:00Z",
    "html_url": "https://github.com/byu-ml-capstone/dinnerbell/pull/22",
}]
app.dependency_overrides[get_github_client] = lambda: github
original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def preview_lifespan(application):
    async with original_lifespan(application):
        with SessionLocal() as db:
            name = "GitHub links UI demo (MOCK)"
            if not db.query(Project).filter_by(name=name).first():
                user = db.query(User).filter_by(username="taylor").one()
                project = Project(
                    name=name,
                    description="MOCK GitHub responses for UI testing; no real GitHub requests",
                    owner_id=user.id,
                    github_repo_url="https://github.com/byu-ml-capstone/dinnerbell",
                )
                db.add(project)
                db.flush()
                db.add(ProjectMember(project_id=project.id, user_id=user.id, role="member"))
                for title, branch in (
                    ("Open PR (mock)", "alice/grocery-list"),
                    ("Merged PR, deleted branch (mock)", "alice/recipe-search"),
                    ("Closed PR (mock)", "alice/closed"),
                    ("Branch exists, no PR (mock)", "alice/login-page"),
                    ("Branch not found (mock)", "alice/missing"),
                ):
                    db.add(Story(project_id=project.id, title=title, github_branch=branch, status="backlog"))
                db.commit()
        yield


app.router.lifespan_context = preview_lifespan

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
