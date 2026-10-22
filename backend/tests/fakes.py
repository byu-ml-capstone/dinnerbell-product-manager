"""Fakes for the AI and GitHub clients (TEST-4). Nothing in the test suite touches the network."""

import base64
import json
import re
from datetime import datetime
from pathlib import Path

from app.services.github_client import GitHubError
from app.services.llm import LLMError, ReviewTurn, ToolCall

FIXTURES = Path(__file__).parent / "fixtures"


class FakeAnalysisLLM:
    model = "fake-analysis-model"

    def __init__(self, text: str = "## Summary\nOn track.", error: Exception | None = None):
        self.text = text
        self.error = error
        self.prompts: list[tuple[str, str]] = []

    def complete(self, system: str, user: str):
        self.prompts.append((system, user))
        if self.error:
            raise self.error
        return self.text, {"prompt_tokens": 100, "completion_tokens": 50}


def timeout_error() -> LLMError:
    return LLMError("Request timed out after one retry")


def tool_turn(name: str, call_id: str = "call-1", **arguments) -> ReviewTurn:
    args = json.dumps(arguments)
    return ReviewTurn(
        tool_calls=[ToolCall(call_id=call_id, name=name, arguments=args)],
        text=None,
        output_items=[{"type": "function_call", "call_id": call_id, "name": name, "arguments": args}],
        usage={"input_tokens": 10, "output_tokens": 5},
    )


def verdict_turn(verdict: str, evidence: list[dict] | None = None, criteria: list[dict] | None = None,
                 summary: str = "Reviewed.", has_tests: bool | None = True) -> ReviewTurn:
    payload = {
        "verdict": verdict,
        "summary": summary,
        "criteria": criteria or [],
        "evidence": evidence or [],
        "has_tests": has_tests,
    }
    return ReviewTurn(tool_calls=[], text=json.dumps(payload), output_items=[], usage={"input_tokens": 20, "output_tokens": 10})


class FakeReviewLLM:
    """Serves scripted turns per story title. Summary calls (no tools) return `summary`."""

    model = "fake-codex-model"

    def __init__(self, scripts: dict[str, list[ReviewTurn]] | None = None, summary: str = "## Sprint review\nAll reviewed."):
        self.scripts = {title: list(turns) for title, turns in (scripts or {}).items()}
        self.summary = summary
        self.calls: list[dict] = []
        self.tool_outputs: dict[str, list[str]] = {}

    def run_turn(self, instructions, input_items, tools, json_schema=None) -> ReviewTurn:
        if not tools:
            self.calls.append({"kind": "summary", "input": input_items})
            return ReviewTurn(tool_calls=[], text=self.summary, usage={"input_tokens": 5, "output_tokens": 5})
        context = input_items[0]["content"]
        title = re.search(r"^Title: (.*)$", context, re.M).group(1)
        self.calls.append({"kind": "story", "title": title, "context": context})
        self.tool_outputs[title] = [
            item["output"] for item in input_items if isinstance(item, dict) and item.get("type") == "function_call_output"
        ]
        turns = self.scripts.get(title)
        if not turns:
            raise AssertionError(f"No scripted turn left for story {title!r}")
        return turns.pop(0)

    def story_calls(self, title: str) -> int:
        return sum(1 for call in self.calls if call.get("title") == title)


class FakeGitHub:
    """Serves recorded GitHub API responses from tests/fixtures/github/repo.json."""

    def __init__(self, fixture: str = "repo.json"):
        data = json.loads((FIXTURES / "github" / fixture).read_text())
        self.owner = data["owner"]
        self.repo = data["repo"]
        self.branches = data["branches"]
        self.pulls = data["pulls"]
        self.pull_files = data["pull_files"]
        self.files = data["files"]
        self.trees = data["trees"]
        self.merged = data["merged_pulls"]
        self.calls: list[tuple] = []
        self.fail = False

    def _record(self, method: str, owner: str, repo: str, *args):
        self.calls.append((method, owner, repo, *args))
        if self.fail:
            raise GitHubError("GitHub returned 500")
        assert (owner, repo) == (self.owner, self.repo), f"Unexpected repo {owner}/{repo}"

    def get_branch(self, owner, repo, branch):
        self._record("get_branch", owner, repo, branch)
        return self.branches.get(branch)

    def find_pulls_for_branch(self, owner, repo, branch):
        self._record("find_pulls_for_branch", owner, repo, branch)
        return self.pulls.get(branch, [])

    def get_pull_files(self, owner, repo, number):
        self._record("get_pull_files", owner, repo, number)
        return self.pull_files.get(str(number), [])

    def compare(self, owner, repo, base, head):
        self._record("compare", owner, repo, base, head)
        return {"files": []}

    def get_contents(self, owner, repo, path, ref):
        self._record("get_contents", owner, repo, path, ref)
        if path in self.files:
            content = base64.b64encode(self.files[path].encode()).decode()
            return {"type": "file", "path": path, "encoding": "base64", "content": content}
        children = [name for name in self.files if name.startswith(f"{path}/")] if path else list(self.files)
        if children:
            return [{"type": "file", "path": name, "name": name.split("/")[-1]} for name in children]
        return None

    def get_tree(self, owner, repo, ref):
        self._record("get_tree", owner, repo, ref)
        return [{"path": path, "type": "blob"} for path in self.trees.get(ref, list(self.files))]

    def list_commits(self, owner, repo, ref, since=None, until=None):
        self._record("list_commits", owner, repo, ref)
        return []

    def merged_pulls(self, owner, repo, base, since, until):
        self._record("merged_pulls", owner, repo, base)
        result = []
        for pull in self.merged:
            merged_at = datetime.fromisoformat(pull["merged_at"].replace("Z", "+00:00"))
            if since <= merged_at < until:
                result.append(pull)
        return result
