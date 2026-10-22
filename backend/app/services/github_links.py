"""Parsing and checking GitHub repo URLs and story branches (GH-4, GH-6). No network calls here."""

import re

from fastapi import HTTPException

REPO_PATTERN = re.compile(r"^https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)$")
BRANCH_URL_PATTERN = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/tree/(.+)$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")


def normalize_repo_url(value: str | None) -> str | None:
    """Returns the canonical repo URL, None to clear it, or raises 422."""
    if value is None or not value.strip():
        return None
    url = value.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4].rstrip("/")
    if not REPO_PATTERN.match(url):
        raise HTTPException(status_code=422, detail="Repository URL must look like https://github.com/<owner>/<repo>")
    return url


def parse_repo(repo_url: str) -> tuple[str, str]:
    match = REPO_PATTERN.match(repo_url)
    if not match:
        raise ValueError(f"Not a GitHub repository URL: {repo_url}")
    return match.group(1), match.group(2)


def normalize_branch(value: str | None, repo_url: str | None) -> str | None:
    """Accepts a branch name or a /tree/<branch> URL for the project's repo; stores only the name."""
    if value is None or not value.strip():
        return None
    branch = value.strip()
    match = BRANCH_URL_PATTERN.match(branch)
    if match:
        owner, repo, branch = match.group(1), match.group(2), match.group(3).rstrip("/")
        if repo_url:
            project_owner, project_repo = parse_repo(repo_url)
            if (owner.lower(), repo.lower()) != (project_owner.lower(), project_repo.lower()):
                raise HTTPException(status_code=400, detail="Branch URL is for a different repository")
    if not BRANCH_PATTERN.match(branch) or ".." in branch:
        raise HTTPException(status_code=400, detail="Branch names may only use letters, numbers, '.', '_', '-' and '/'")
    return branch


def branch_url(repo_url: str | None, branch: str | None) -> str | None:
    if not repo_url or not branch:
        return None
    return f"{repo_url}/tree/{branch}"


def slugify(title: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:limit].strip("-")


def suggested_branch(username: str, title: str) -> str:
    """Our convention: name of developer combined with task (D-6)."""
    return f"{username}/{slugify(title)}"
