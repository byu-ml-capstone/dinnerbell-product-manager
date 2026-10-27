"""Manual prompt check (AI-12, REPO-14). Uses the real AI settings from the environment; never run in CI.

    cd backend
    python -m scripts.ai_eval                    # run the analysis prompt on the three sample sprints
    python -m scripts.ai_eval --review SPRINT_ID # run a real sprint review against the configured DATABASE_URL

Outputs land in backend/ai_eval_out/<timestamp>/ so runs before and after a prompt change can be compared.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from app.database import SessionLocal
from app.models import Sprint, SprintReview
from app.services.analysis import generate_analysis
from app.services.analysis_grounding import prepare_snapshot
from app.services.github_client import get_github_client
from app.services.llm import get_analysis_llm, get_review_llm
from app.services.sprint_review import run_review

BACKEND_DIR = Path(__file__).resolve().parents[1]
SAMPLES = BACKEND_DIR / "tests" / "fixtures" / "sprints"


def output_dir() -> Path:
    path = BACKEND_DIR / "ai_eval_out" / datetime.now().strftime("%Y%m%d-%H%M%S")
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_samples() -> int:
    llm = get_analysis_llm()
    if llm is None:
        print("Set OPENAI_API_KEY (or ANALYSIS_LLM_API_KEY), ANALYSIS_LLM_BASE_URL and ANALYSIS_LLM_MODEL first.", file=sys.stderr)
        return 1
    out = output_dir()
    for sample in sorted(SAMPLES.glob("*.json")):
        snapshot = prepare_snapshot(json.loads(sample.read_text(encoding="utf-8")))
        text, usage = generate_analysis(llm, snapshot)
        (out / f"{sample.stem}.md").write_text(text, encoding="utf-8")
        print(f"{sample.stem}: {len(text.split())} words, usage {usage}")
    print(f"Wrote {out}")
    return 0


def run_sprint_review(sprint_id: str) -> int:
    llm, github = get_review_llm(), get_github_client()
    if llm is None or github is None:
        print("Set OPENAI_API_KEY (or REVIEW_LLM_API_KEY), REVIEW_LLM_MODEL and GITHUB_TOKEN first.", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        sprint = db.get(Sprint, sprint_id)
        if sprint is None or not sprint.project.github_repo_url:
            print("Sprint not found, or its project has no GitHub repository.", file=sys.stderr)
            return 1
        review = SprintReview(sprint_id=sprint.id, status="pending", model=llm.model, repo_url=sprint.project.github_repo_url)
        db.add(review)
        db.commit()
        review_id = review.id
    run_review(review_id, llm, github)
    with SessionLocal() as db:
        review = db.get(SprintReview, review_id)
        result = {
            "status": review.status,
            "error": review.error,
            "summary": review.summary_markdown,
            "unlinked_work": review.unlinked_work,
            "usage": review.usage,
            "items": [
                {"story": item.story_title, "verdict": item.verdict, "summary": item.summary, "evidence": item.evidence}
                for item in review.items
            ],
        }
    out = output_dir()
    (out / f"review-{sprint_id}.json").write_text(json.dumps(result, indent=2, default=str))
    print(f"Review {review_id}: {result['status']}. Wrote {out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review", metavar="SPRINT_ID", help="run a real sprint review for this sprint")
    args = parser.parse_args()
    return run_sprint_review(args.review) if args.review else run_samples()


if __name__ == "__main__":
    sys.exit(main())
