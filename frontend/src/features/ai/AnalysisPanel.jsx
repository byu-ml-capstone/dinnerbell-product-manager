import { useEffect, useState } from "react";
import { Bot, RotateCcw, Save } from "lucide-react";
import { analysesApi } from "../../api/analyses";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { MarkdownText } from "../../components/MarkdownText";
import { Spinner } from "../../components/Spinner";
import { formatDateTime } from "../../format";
import { useWorkspace } from "../../workspace";
import { usePolling } from "./usePolling";

const RUNNING = ["pending", "running"];
const NONE = [];

export function AnalysisPanel({ sprint }) {
  const { version } = useWorkspace();
  const list = useAsync(() => analysesApi.list(sprint.id), [sprint.id, version]);
  const [selectedId, setSelectedId] = useState(null);
  const [context, setContext] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const analyses = list.data || NONE;
  useEffect(() => {
    // Show the newest analysis unless the user picked another one that still exists.
    if (!analyses.some((item) => item.id === selectedId)) setSelectedId(analyses[0]?.id || null);
  }, [analyses, selectedId]);

  usePolling(analyses.some((item) => RUNNING.includes(item.status)), list.reload);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const created = await analysesApi.create(sprint.id, context);
      setContext("");
      await list.reload();
      setSelectedId(created.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="report-grid">
      <div className="panel">
        <label className="field">
          <span>Additional context</span>
          <textarea
            value={context}
            onChange={(event) => setContext(event.target.value)}
            placeholder="Team interruptions, stakeholder notes, risks, or lessons learned"
          />
        </label>
        <button onClick={run} disabled={busy}>
          <Bot size={16} /> Run analysis
        </button>
        <p className="muted">Works mid-sprint and after closing. Every run is kept.</p>
        <FormError message={error || list.error} />
        <div className="history-list">
          {analyses.map((item) => (
            <button key={item.id} className={item.id === selectedId ? "history-item active" : "history-item"} onClick={() => setSelectedId(item.id)}>
              <span>{formatDateTime(item.created_at)}</span>
              <small>
                {item.trigger === "sprint_closed" ? "On close" : item.created_by_name || "Manual"} · {item.final_content ? "final" : item.status}
              </small>
            </button>
          ))}
          {list.data && analyses.length === 0 && <p className="muted">No analyses yet.</p>}
        </div>
      </div>
      {selectedId ? (
        <AnalysisDetail id={selectedId} onRetry={run} onSaved={list.reload} listStatus={analyses.find((item) => item.id === selectedId)?.status} />
      ) : (
        <div className="panel muted">Run an analysis to see it here.</div>
      )}
    </div>
  );
}

function AnalysisDetail({ id, onRetry, onSaved, listStatus }) {
  // Reloads when polling sees the status change.
  const detail = useAsync(() => analysesApi.get(id), [id, listStatus]);
  const [content, setContent] = useState("");
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const data = detail.data?.id === id ? detail.data : null;

  useEffect(() => {
    setContent(data?.final_content || data?.ai_content || "");
    setEditing(false);
  }, [data?.id, data?.final_content, data?.ai_content]);

  if (!data) return <div className="panel">{detail.error ? <FormError message={detail.error} /> : <Spinner />}</div>;

  async function save() {
    setError("");
    try {
      await analysesApi.save(id, content);
      await detail.reload();
      setEditing(false);
      await onSaved();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="panel report-editor">
      <div className="section-heading">
        <strong>
          {data.final_content
            ? `Final (saved by ${data.finalized_by_name || "someone"} on ${formatDateTime(data.finalized_at)})`
            : "AI draft"}
        </strong>
        <span className="muted">{data.model}</span>
      </div>
      {RUNNING.includes(data.status) && <Spinner label="The AI is writing the analysis…" />}
      {data.status === "failed" && (
        <div className="failed-box">
          <FormError message={`The analysis failed: ${data.error}`} />
          <button className="secondary-button compact" onClick={onRetry}>
            <RotateCcw size={14} /> Retry
          </button>
        </div>
      )}
      {data.status === "complete" &&
        (editing ? (
          <>
            <textarea value={content} onChange={(event) => setContent(event.target.value)} />
            <div className="button-row">
              <button className="secondary-button" onClick={() => setEditing(false)}>
                Cancel
              </button>
              <button disabled={!content.trim()} onClick={save}>
                <Save size={16} /> Save final
              </button>
            </div>
          </>
        ) : (
          <>
            <MarkdownText text={content} />
            <div className="button-row">
              <button className="secondary-button" onClick={() => setEditing(true)}>
                Edit and save as final
              </button>
            </div>
          </>
        ))}
      <FormError message={error} />
      <details className="data-sent">
        <summary>Data sent to the AI</summary>
        <pre>{JSON.stringify(data.input_snapshot, null, 2)}</pre>
      </details>
    </div>
  );
}
