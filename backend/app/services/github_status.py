"""Story branch and PR lookup with a five-minute cache (GH-5, GH-8)"""

import time

from fastapi import HTTPException

from ..schemas.github import PullRequestInfo, StoryGitHubStatus
from .github_client import GitHubClient, GitHubError
from .github_links import branch_url, parse_repo

CACHE_SECONDS = 5 * 60
_status_cache: dict[tuple[str, str], tuple[float, StoryGitHubStatus]] = {}


def clear_cache() -> None:
    _status_cache.clear()


def lookup_status(repo_url: str | None, branch: str | None, github: GitHubClient | None) -> StoryGitHubStatus:
    if not branch:
        raise HTTPException(status_code=400, detail="This story has no branch")
    if not repo_url:
        raise HTTPException(status_code=400, detail="Set the project's GitHub repository in Settings first")
    if github is None:
        raise HTTPException(status_code=503, detail="GitHub token not configured")

    key = (repo_url, branch)
    cached = _status_cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    owner, repo = parse_repo(repo_url)
    try:
        pulls = github.find_pulls_for_branch(owner, repo, branch)
        branch_exists = github.get_branch(owner, repo, branch) is not None
    except GitHubError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    pull = max(pulls, key=lambda item: item.get("created_at") or "") if pulls else None
    status = StoryGitHubStatus(
        branch=branch,
        branch_url=branch_url(repo_url, branch),
        branch_exists=branch_exists,
        pull_request=(
            PullRequestInfo(
                number=pull["number"],
                title=pull.get("title", ""),
                state=pull.get("state", "open"),
                merged=bool(pull.get("merged_at")),
                url=pull.get("html_url", ""),
            )
            if pull
            else None
        ),
    )
    _status_cache[key] = (time.monotonic() + CACHE_SECONDS, status)
    return status
