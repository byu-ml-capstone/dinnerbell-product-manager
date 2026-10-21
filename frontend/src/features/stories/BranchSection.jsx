import { useEffect, useState } from "react";
import { Check, Copy, ExternalLink, GitBranch, GitPullRequest } from "lucide-react";
import { storiesApi } from "../../api/stories";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { useWorkspace } from "../../workspace";

/** The story's branch, its live PR status (GH-8) and the suggested name with Copy / Use this (GH-6). */
export function BranchSection({ story, readOnly }) {
  const { changed } = useWorkspace();
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setStatus(null);
    setStatusError("");
    if (!story.github_branch) return;
    let cancelled = false;
    storiesApi
      .github(story.id)
      .then((data) => !cancelled && setStatus(data))
      .catch((err) => {
        if (cancelled) return;
        if (err.status === 503) setStatusError("GitHub token not configured");
        else if (err.status === 400) setStatusError("Set the GitHub repository in Settings to see PR status");
        else setStatusError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [story.id, story.github_branch]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(story.suggested_branch);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Couldn't copy. Select the name and copy it by hand.");
    }
  }

  async function useSuggestion() {
    setError("");
    try {
      await storiesApi.update(story.id, { github_branch: story.suggested_branch });
      await changed();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="drawer-section">
      <PanelTitle icon={<GitBranch size={16} />} title="Branch" />
      {story.github_branch ? (
        <div className="branch-box">
          {story.branch_url ? (
            <a href={story.branch_url} target="_blank" rel="noreferrer" className="branch-name">
              <GitBranch size={14} /> {story.github_branch} <ExternalLink size={12} />
            </a>
          ) : (
            <span className="branch-name">
              <GitBranch size={14} /> {story.github_branch}
            </span>
          )}
          {status?.pull_request && (
            <a href={status.pull_request.url} target="_blank" rel="noreferrer" className="pr-status">
              <GitPullRequest size={14} /> PR #{status.pull_request.number} ·{" "}
              {status.pull_request.merged ? "merged" : status.pull_request.state}
            </a>
          )}
          {status && !status.pull_request && (
            <span className="muted">{status.branch_exists ? "Branch exists, no PR" : "Branch not found"}</span>
          )}
          {statusError && <span className="muted">{statusError}</span>}
        </div>
      ) : (
        <p className="muted">No branch linked.</p>
      )}
      <div className="suggested-branch">
        <span className="muted">Suggested</span>
        <code>{story.suggested_branch}</code>
        <button className="ghost-button compact" onClick={copy} title="Copy branch name">
          {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy"}
        </button>
        {!readOnly && story.github_branch !== story.suggested_branch && (
          <button className="ghost-button compact" onClick={useSuggestion}>
            Use this
          </button>
        )}
      </div>
      <FormError message={error} />
    </section>
  );
}
