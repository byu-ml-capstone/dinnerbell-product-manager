"""Local-only AI and GitHub UI fixtures, excluded from the production image"""

import json
import re
from contextlib import asynccontextmanager
from datetime import timedelta

import uvicorn

from app.database import SessionLocal
from app.models import Project, ProjectMember, Sprint, Story, User
from app.services import clock
from app.services.events import record_creation
from app.services.llm import get_analysis_llm, get_review_llm

from .fakes import FakeAnalysisLLM, FakeReviewLLM, ReviewTurn, timeout_error, tool_turn, verdict_turn
from .github_ui_preview import app


class DemoAnalysis(FakeAnalysisLLM):
    model = "gpt-6-luna (MOCK)"

    def complete(self, system, user):
        if "simulate timeout" in user.lower():
            raise timeout_error()
        data = json.loads(user.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        metrics = data["metrics"]
        text = "\n\n".join([
            "## Summary\nMOCK AI report for frontend testing. No OpenAI request was made.",
            f"## Progress\nCompleted points: {metrics.get('completed_points', 'unknown')}.",
            "## Velocity\nUse the server-calculated metrics shown below.",
            f"## Estimated Completion\n{metrics.get('estimated_completion_date', 'not enough data')}",
            "## Accomplished\n" + "\n".join(f"- {row['title']}" for row in data["stories"] if row["status"] == "done"),
            "## Remaining Work\nReview the unfinished stories on the board.",
            "## Blockers and Risks\nThis is a fixture, not a real code evaluation.",
            "## Suggested Next Steps\nInspect the draft, edit it, and save a final version.",
        ])
        return text, {"prompt_tokens": 100, "completion_tokens": 100}


class DemoReview(FakeReviewLLM):
    model = "gpt-6-luna (MOCK)"

    def run_turn(self, instructions, input_items, tools, json_schema=None):
        if not tools:
            return ReviewTurn(
                tool_calls=[], text="## Sprint review summary\nMOCK evaluation: inspect each story's verdict and evidence. No OpenAI request was made.",
                usage={"input_tokens": 50, "output_tokens": 30},
            )
        context = input_items[0]["content"]
        if not any(item.get("type") == "function_call_output" for item in input_items):
            number = int(re.search(r"Pull request: #(\d+)", context).group(1))
            return tool_turn("get_pull_request_files", pr_number=number)
        if "Title: Recipe search API (mock)" in context:
            return verdict_turn("matches", evidence=[{
                "path": "backend/app/recipes.py", "lines": "1-4", "commit": None, "note": "Mock search implementation",
            }], summary="Mock evidence supports the story.")
        if "Title: Grocery list (mock)" in context:
            return verdict_turn("partial", evidence=[{
                "path": "backend/app/grocery.py", "lines": "1-4", "commit": None, "note": "Mock grocery implementation",
            }], summary="Mock evidence supports part of the acceptance criteria.")
        return verdict_turn("no_evidence", summary="Mock fixture contains no matching implementation.", has_tests=False)


app.dependency_overrides[get_analysis_llm] = lambda: DemoAnalysis()
app.dependency_overrides[get_review_llm] = lambda: DemoReview()
previous_lifespan = app.router.lifespan_context


@asynccontextmanager
async def ai_preview_lifespan(application):
    async with previous_lifespan(application):
        with SessionLocal() as db:
            if not db.query(Project).filter_by(name="AI sprint demo (MOCK)").first():
                user = db.query(User).filter_by(username="taylor").one()
                project = Project(
                    name="AI sprint demo (MOCK)", owner_id=user.id,
                    description="MOCK AI and GitHub; no paid API calls. Use Board → AI for Sprint. Context 'simulate timeout' tests Retry.",
                    github_repo_url="https://github.com/byu-ml-capstone/dinnerbell",
                )
                db.add(project)
                db.flush()
                db.add(ProjectMember(project_id=project.id, user_id=user.id, role="member"))
                today = clock.today()
                sprint = Sprint(
                    project_id=project.id, name="AI demo sprint", goal="Verify the AI frontend",
                    start_date=today - timedelta(days=3), end_date=today + timedelta(days=10),
                )
                db.add(sprint)
                db.add(Sprint(
                    project_id=project.id, name="Next demo sprint", goal="Check sprint switching",
                    start_date=today + timedelta(days=11), end_date=today + timedelta(days=24),
                ))
                db.flush()
                for title, status, points, branch in (
                    ("Recipe search API (mock)", "done", 5, "alice/recipe-search"),
                    ("Grocery list (mock)", "in_progress", 3, "alice/grocery-list"),
                    ("Pantry tracking (mock)", "selected", 2, "alice/pantry-tracking"),
                    ("No linked code (mock)", "selected", 1, None),
                ):
                    story = Story(
                        project_id=project.id, sprint_id=sprint.id, title=title, status=status, story_points=points,
                        assignee_id=user.id, github_branch=branch, acceptance_criteria="Implement the described feature with tests",
                    )
                    db.add(story)
                    db.flush()
                    record_creation(db, story, user.id)
                db.commit()
        yield


app.router.lifespan_context = ai_preview_lifespan

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
