/** Local downloads use the selected report, never another run's current data. */
export function reportFilename(kind, sprintName, id, extension = "md") {
  const name = (sprintName || "sprint").normalize("NFKC").replace(/[<>:"/\\|?*\x00-\x1f]/g, "-").replace(/\s+/g, "-").replace(/[. ]+$/g, "").slice(0, 80);
  return `${kind}-${name}-${id}.${extension}`;
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Give the browser time to begin the download before releasing the object URL.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadMarkdown(content, filename) {
  downloadBlob(new Blob([content.endsWith("\n") ? content : `${content}\n`], { type: "text/markdown;charset=utf-8" }), filename);
}

export function reviewMarkdown(review, repoUrl) {
  const lines = ["# Sprint Code Review", `Generated: ${review.created_at}`, `Model: ${review.model}`, "> AI advice only. Code evidence does not establish deployed or user validation."];
  if (review.summary_markdown) lines.push(review.summary_markdown);
  const base = review.repo_url || repoUrl;
  for (const item of review.items) {
    lines.push(`## ${item.story_title}`, `Claimed status: ${item.claimed_status}\n\nVerdict: ${item.verdict}`, item.summary || "No summary recorded.");
    if (item.branch) lines.push(`Branch: ${item.branch}`);
    if (item.pr_number) lines.push(`PR: ${base}/pull/${item.pr_number}`);
    if (item.head_sha) lines.push(`Commit: ${item.head_sha}`);
    if (item.criteria.length) lines.push("### Acceptance Criteria", item.criteria.map((entry) => `- **${entry.status}** ${entry.criterion}${entry.evidence ? ` — ${entry.evidence}` : ""}`).join("\n"));
    if (item.evidence.length) lines.push("### Evidence", item.evidence.map((entry) => {
      const anchor = entry.lines ? `#L${entry.lines.replace(/\s/g, "").replace("-", "-L")}` : "";
      const url = entry.path && item.head_sha ? `${base}/blob/${item.head_sha}/${entry.path}${anchor}` : entry.commit ? `${base}/commit/${entry.commit}` : "";
      return `- ${entry.path || entry.commit || "Evidence"}${url ? ` (${url})` : ""}${entry.note ? ` — ${entry.note}` : ""}`;
    }).join("\n"));
    if (item.has_tests != null) lines.push(`Tests in the change: ${item.has_tests ? "yes" : "no"}`);
  }
  lines.push("## Merged Work Not Linked to a Story", review.unlinked_work.length ? review.unlinked_work.map((pull) => `- [#${pull.pr_number} ${pull.title}](${pull.url}) by ${pull.author || "unknown"}, merged ${pull.merged_at}`).join("\n") : "None recorded.");
  return lines.join("\n\n") + "\n";
}
