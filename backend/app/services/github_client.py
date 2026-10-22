"""Read-only GitHub REST client. It only ever talks to api.github.com with owner/repo/ref values the
server parsed itself; it never fetches a URL a user typed (GH-4, REPO-12)."""

from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import Depends, HTTPException

from ..config import settings

API_BASE = "https://api.github.com"


class GitHubError(Exception):
    pass


def _quote_path(value: str) -> str:
    return quote(value, safe="/")


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class GitHubClient:
    def __init__(self, token: str, http: httpx.Client | None = None):
        self.http = http or httpx.Client(
            base_url=API_BASE,
            timeout=20,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    def _get(self, path: str, params: dict | None = None, allow_404: bool = False):
        try:
            response = self.http.get(path, params=params)
        except httpx.HTTPError as exc:
            raise GitHubError(f"Couldn't reach GitHub: {exc}") from exc
        if response.status_code == 404 and allow_404:
            return None
        if response.status_code >= 400:
            raise GitHubError(f"GitHub returned {response.status_code} for {path}")
        return response.json()

    def get_branch(self, owner: str, repo: str, branch: str) -> dict | None:
        return self._get(f"/repos/{owner}/{repo}/branches/{_quote_path(branch)}", allow_404=True)

    def find_pulls_for_branch(self, owner: str, repo: str, branch: str) -> list[dict]:
        pulls = self._get(f"/repos/{owner}/{repo}/pulls", {"state": "all", "head": f"{owner}:{branch}", "per_page": 10}) or []
        return sorted(pulls, key=lambda pull: pull.get("created_at") or "", reverse=True)

    def get_pull_files(self, owner: str, repo: str, number: int) -> list[dict]:
        files: list[dict] = []
        for page in range(1, 4):
            batch = self._get(f"/repos/{owner}/{repo}/pulls/{number}/files", {"per_page": 100, "page": page}) or []
            files.extend(batch)
            if len(batch) < 100:
                break
        return files

    def compare(self, owner: str, repo: str, base: str, head: str) -> dict:
        return self._get(f"/repos/{owner}/{repo}/compare/{_quote_path(base)}...{_quote_path(head)}") or {}

    def get_contents(self, owner: str, repo: str, path: str, ref: str):
        return self._get(f"/repos/{owner}/{repo}/contents/{_quote_path(path)}", {"ref": ref}, allow_404=True)

    def get_tree(self, owner: str, repo: str, ref: str) -> list[dict]:
        data = self._get(f"/repos/{owner}/{repo}/git/trees/{_quote_path(ref)}", {"recursive": "1"}) or {}
        return data.get("tree", [])

    def list_commits(self, owner: str, repo: str, ref: str, since: str | None = None, until: str | None = None) -> list[dict]:
        params = {"sha": ref, "per_page": 50}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self._get(f"/repos/{owner}/{repo}/commits", params) or []

    def merged_pulls(self, owner: str, repo: str, base: str, since: datetime, until: datetime) -> list[dict]:
        """PRs merged into `base` within [since, until)."""
        merged: list[dict] = []
        for page in range(1, 6):
            pulls = self._get(
                f"/repos/{owner}/{repo}/pulls",
                {"state": "closed", "base": base, "sort": "updated", "direction": "desc", "per_page": 100, "page": page},
            ) or []
            for pull in pulls:
                merged_at = _parse_time(pull.get("merged_at"))
                if merged_at and since <= merged_at < until:
                    merged.append(pull)
            oldest_update = _parse_time(pulls[-1].get("updated_at")) if pulls else None
            if len(pulls) < 100 or (oldest_update and oldest_update < since):
                break
        return merged


def get_github_client() -> GitHubClient | None:
    if not settings.github_token:
        return None
    return GitHubClient(settings.github_token)


def require_github_client(client: GitHubClient | None = Depends(get_github_client)) -> GitHubClient:
    if client is None:
        raise HTTPException(status_code=503, detail="GitHub token not configured. Set GITHUB_TOKEN.")
    return client
