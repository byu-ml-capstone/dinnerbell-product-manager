import { Fragment, useEffect, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink, ScanSearch } from "lucide-react";
import { reviewsApi } from "../../api/reviews";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { MarkdownText } from "../../components/MarkdownText";
import { Spinner } from "../../components/Spinner";
import { STATUS_LABELS } from "../../constants";
import { formatDateTime } from "../../format";
import { useWorkspace } from "../../workspace";
import { usePolling } from "./usePolling";

const RUNNING = ["pending", "running"];
const NONE = [];
export const VERDICTS = {
  matches: { label: "Matches", tone: "good" },
  partial: { label: "Partial", tone: "warn" },
  no_evidence: { label: "No evidence", tone: "bad" },
  no_link: { label: "No link", tone: "muted" },
  cant_tell: { label: "Can't tell", tone: "outline" },
};

/** Advice-only check of each story's code against its claimed status (§10.2, D-36). */
export function SprintReviewPanel({ sprint }) {
  const { project, version } = useWorkspace();
  const list = useAsync(() => reviewsApi.list(sprint.id), [sprint.id, version]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const reviews = list.data || NONE;
  const running = reviews.some((item) => RUNNING.includes(item.status));

  useEffect(() => {
    if (!reviews.some((item) => item.id === selectedId)) setSelectedId(reviews[0]?.id || null);
  }, [reviews, selectedId]);

  usePolling(running, list.reload);

  async function start() {
    setBusy(true);
    setError("");
    try {
      const created = await reviewsApi.start(sprint.id);
      setSelectedId(created.id);
      await list.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const disabledReason = !project.github_repo_url
    ? "Set the GitHub repository in Settings first."
    : running
      ? "A review is already running."
      : "";

  return (
    <div className="panel review-panel">
      <div className="section-heading">
        <div className="button-row">
          <button onClick={start} disabled={busy || Boolean(disabledReason)} title={disabledReason}>
            <ScanSearch size={16} /> Run sprint review
          </button>
          {reviews.length > 1 && (
            <select value={selectedId || ""} onChange={(event) => setSelectedId(event.target.value)} aria-label="Past reviews">
              {reviews.map((item) => (
                <option key={item.id} value={item.id}>
                  {formatDateTime(item.created_at)} · {item.status}
                </option>
              ))}
            </select>
          )}
        </div>
        {disabledReason && <span className="muted">{disabledReason}</span>}
      </div>
      <p className="muted">
        The AI reads each story's linked branch or PR and says whether the code supports the story's status. It's advice only and never
        changes a story.
      </p>
      <FormError message={error || list.error} />
      {selectedId ? (
        <ReviewDetail id={selectedId} repoUrl={project.github_repo_url} listStatus={reviews.find((item) => item.id === selectedId)?.status} itemsDone={reviews.find((item) => item.id === selectedId)?.items_done} />
      ) : (
        list.data && <p className="muted">No sprint reviews yet.</p>
      )}
    </div>
  );
}

function ReviewDetail({ id, repoUrl, listStatus, itemsDone }) {
  const detail = useAsync(() => reviewsApi.get(id), [id, listStatus, itemsDone]);
  const [open, setOpen] = useState({});
  const review = detail.data?.id === id ? detail.data : null;
  if (!review) return detail.error ? <FormError message={detail.error} /> : <Spinner />;

  const evidenceUrl = (item, entry) => {
    const base = review.repo_url || repoUrl;
    if (entry.path && item.head_sha) {
      const lines = entry.lines ? `#L${entry.lines.replace(/\s/g, "").replace("-", "-L")}` : "";
      return `${base}/blob/${item.head_sha}/${entry.path}${lines}`;
    }
    if (entry.commit) return `${base}/commit/${entry.commit}`;
    return null;
  };

  return (
    <div className="review-detail">
      {RUNNING.includes(review.status) && (
        <div className="progress">
          <Spinner label={`Reviewing ${review.items_done} of ${review.items_total || "?"} stories…`} />
          <div className="progress-bar">
            <i style={{ width: `${review.items_total ? (100 * review.items_done) / review.items_total : 5}%` }} />
          </div>
        </div>
      )}
      {review.status === "failed" && <FormError message={`The review failed: ${review.error}`} />}
      {review.summary_markdown && <MarkdownText text={review.summary_markdown} />}
      {review.items.length > 0 && (
        <table className="data-table review-table">
          <thead>
            <tr>
              <th />
              <th>Story</th>
              <th>Claimed</th>
              <th>Verdict</th>
              <th>PR</th>
            </tr>
          </thead>
          <tbody>
            {review.items.map((item) => {
              const verdict = VERDICTS[item.verdict] || { label: item.verdict, tone: "outline" };
              const expanded = open[item.id];
              const mismatch = item.claimed_status === "done" && item.verdict !== "matches";
              return (
                <Fragment key={item.id}>
                  <tr className="clickable" onClick={() => setOpen({ ...open, [item.id]: !expanded })}>
                    <td>{expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                    <td>
                      {item.story_title}
                      {item.reused_from_item_id && <span className="muted"> (unchanged since last review)</span>}
                    </td>
                    <td>{STATUS_LABELS[item.claimed_status] || item.claimed_status}</td>
                    <td>
                      <span className={`verdict ${verdict.tone}`}>{verdict.label}</span>
                      {mismatch && (
                        <span className="mismatch" title="Marked done, but the code doesn't show it">
                          <AlertTriangle size={14} />
                        </span>
                      )}
                    </td>
                    <td>
                      {item.pr_number ? (
                        <a href={`${review.repo_url}/pull/${item.pr_number}`} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()}>
                          #{item.pr_number}
                        </a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="expanded-row">
                      <td />
                      <td colSpan={4}>
                        {mismatch && <p className="warning-line">Marked done, but the code doesn't show it.</p>}
                        <p>{item.summary}</p>
                        {item.criteria.length > 0 && (
                          <ul className="criteria-list">
                            {item.criteria.map((criterion, index) => (
                              <li key={index} className={`criterion ${criterion.status}`}>
                                <strong>{criterion.status.replace("_", " ")}</strong> {criterion.criterion}
                                {criterion.evidence && <span className="muted"> — {criterion.evidence}</span>}
                              </li>
                            ))}
                          </ul>
                        )}
                        {item.evidence.length > 0 && (
                          <ul className="evidence-list">
                            {item.evidence.map((entry, index) => {
                              const url = evidenceUrl(item, entry);
                              const label = entry.path ? `${entry.path}${entry.lines ? `:${entry.lines}` : ""}` : entry.commit?.slice(0, 7);
                              return (
                                <li key={index}>
                                  {url ? (
                                    <a href={url} target="_blank" rel="noreferrer">
                                      {label} <ExternalLink size={11} />
                                    </a>
                                  ) : (
                                    label
                                  )}
                                  {entry.note && <span className="muted"> — {entry.note}</span>}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                        {item.has_tests != null && <p className="muted">Tests in the change: {item.has_tests ? "yes" : "no"}</p>}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}
      {review.status === "complete" && (
        <div className="unlinked">
          <h4>Merged work not linked to a story</h4>
          {review.unlinked_work.length === 0 ? (
            <p className="muted">None.</p>
          ) : (
            <ul>
              {review.unlinked_work.map((pull) => (
                <li key={pull.pr_number}>
                  <a href={pull.url} target="_blank" rel="noreferrer">
                    #{pull.pr_number} {pull.title}
                  </a>{" "}
                  <span className="muted">
                    by {pull.author || "unknown"}, merged {formatDateTime(pull.merged_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
