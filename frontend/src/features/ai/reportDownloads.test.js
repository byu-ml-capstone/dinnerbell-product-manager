import assert from "node:assert/strict";
import { test } from "node:test";
import { downloadMarkdown, reportFilename, reviewMarkdown } from "./reportDownloads.js";

test("filenames preserve Chinese and remove Windows forbidden characters", () => {
  assert.equal(reportFilename("analysis", '第一轮 / test:*?"<>|', "run-1"), "analysis-第一轮---test--------run-1.md");
  assert.equal(reportFilename("sprint-report", "Sprint 1", "run-2", "pptx"), "sprint-report-Sprint-1-run-2.pptx");
});

test("review export includes collapsed criteria, commit-pinned evidence and unlinked work", () => {
  const markdown = reviewMarkdown({
    model: "test-model", created_at: "2026-11-17", summary_markdown: "## Summary\nReviewed.", repo_url: "https://github.com/team/app",
    items: [{ story_title: "匹配", claimed_status: "done", verdict: "matches", summary: "Found code", branch: "feature/match", pr_number: 12, head_sha: "abc123", has_tests: true,
      criteria: [{ status: "met", criterion: "Match products", evidence: "Function found" }],
      evidence: [{ path: "app/match.py", lines: "10-20", note: "Matching function" }, { commit: "def456", note: "Tests" }],
    }],
    unlinked_work: [{ pr_number: 13, title: "Fixture", url: "https://github.com/team/app/pull/13", author: "Eason", merged_at: "2026-11-16" }],
  });
  for (const text of ["匹配", "**met** Match products", "/blob/abc123/app/match.py#L10-L20", "/commit/def456", "/pull/12", "Tests in the change: yes", "#13 Fixture", "AI advice only"]) assert.ok(markdown.includes(text), text);
});

test("review without stories or unlinked work still downloads a useful summary", () => {
  const text = reviewMarkdown({ model: "test", created_at: "today", items: [], unlinked_work: [] }, "https://github.com/team/app");
  assert.ok(text.includes("None recorded."));
});

test("Markdown download uses UTF-8 blob, selected text and cleans up URL", async () => {
  let blob;
  let clicked = false;
  let removed = false;
  let revoked;
  let cleanup;
  const link = { click() { clicked = true; }, remove() { removed = true; } };
  const original = { document: globalThis.document, create: URL.createObjectURL, revoke: URL.revokeObjectURL, timeout: globalThis.setTimeout };
  try {
    globalThis.document = { createElement: () => link, body: { appendChild() {} } };
    URL.createObjectURL = (value) => { blob = value; return "blob:test"; };
    URL.revokeObjectURL = (value) => { revoked = value; };
    globalThis.setTimeout = (callback) => { cleanup = callback; };
    downloadMarkdown("# 已审核报告", "selected.md");
    assert.equal(await blob.text(), "# 已审核报告\n");
    assert.equal(blob.type, "text/markdown;charset=utf-8");
    assert.equal(link.download, "selected.md");
    assert.equal(link.href, "blob:test");
    assert.ok(clicked && removed);
    cleanup();
    assert.equal(revoked, "blob:test");
  } finally {
    globalThis.document = original.document;
    URL.createObjectURL = original.create;
    URL.revokeObjectURL = original.revoke;
    globalThis.setTimeout = original.timeout;
  }
});
