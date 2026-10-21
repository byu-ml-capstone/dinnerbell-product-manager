import { useState } from "react";
import { Lock } from "lucide-react";
import { sprintsApi } from "../../api/sprints";
import { FormError } from "../../components/ErrorBanner";
import { Modal } from "../../components/Modal";
import { pluralize } from "../../format";

export function CloseSprintDialog({ sprint, unfinishedCount, onClose, onClosed, onMoveUnfinished }) {
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  async function closeSprint() {
    setBusy(true);
    setError("");
    try {
      const closed = await sprintsApi.close(sprint.id, notes);
      setResult(closed);
      await onClosed(closed);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Modal title={`${sprint.name} closed`} onClose={onClose}>
        <dl className="details">
          <div>
            <dt>Velocity</dt>
            <dd>{result.velocity} pts</dd>
          </div>
          <div>
            <dt>Committed</dt>
            <dd>{result.committed_points ?? "—"} pts</dd>
          </div>
          <div>
            <dt>Completed stories</dt>
            <dd>{result.completed_stories}</dd>
          </div>
          <div>
            <dt>Left in sprint</dt>
            <dd>{result.incomplete_stories}</dd>
          </div>
        </dl>
        {result.unpointed_done_stories > 0 && (
          <p className="warning-line">{pluralize(result.unpointed_done_stories, "done story")} had no points and counted as 0.</p>
        )}
        <p className="muted">
          {result.analysis_id ? "AI analysis started. It will appear in the Analysis tab below." : "AI analysis isn't configured, so none was started."}
        </p>
        <div className="modal-actions">
          {result.incomplete_stories > 0 && (
            <button className="secondary-button" onClick={onMoveUnfinished}>
              Move unfinished stories…
            </button>
          )}
          <button onClick={onClose}>Done</button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title={`Close ${sprint.name}?`} onClose={onClose}>
      <p>
        Closing freezes this sprint's velocity and starts an AI analysis.
        {unfinishedCount > 0 &&
          ` ${pluralize(unfinishedCount, "unfinished story")} will stay in the sprint until someone moves ${unfinishedCount === 1 ? "it" : "them"} out.`}
      </p>
      <label className="field">
        <span>Closing notes</span>
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="What happened this sprint?" />
      </label>
      <FormError message={error} />
      <div className="modal-actions">
        <button className="secondary-button" onClick={onClose}>
          Cancel
        </button>
        <button onClick={closeSprint} disabled={busy}>
          <Lock size={16} /> Close sprint
        </button>
      </div>
    </Modal>
  );
}
