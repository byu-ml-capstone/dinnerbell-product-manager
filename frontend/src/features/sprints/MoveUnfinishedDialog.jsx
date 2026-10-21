import { useState } from "react";
import { sprintsApi } from "../../api/sprints";
import { FormError } from "../../components/ErrorBanner";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/Toast";
import { pluralize, sprintDates } from "../../format";
import { useWorkspace } from "../../workspace";

/** Carry every unfinished story out of a sprint, usually a closed one (MOVE-12, D-28). */
export function MoveUnfinishedDialog({ sprint, onClose }) {
  const { sprints, changed } = useWorkspace();
  const { show, warn } = useToast();
  const targets = sprints.filter((item) => item.status !== "closed" && item.id !== sprint.id);
  const [target, setTarget] = useState(targets.sort((a, b) => a.start_date.localeCompare(b.start_date))[0]?.id || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function move() {
    setBusy(true);
    setError("");
    try {
      const result = await sprintsApi.moveUnfinished(sprint.id, target || null);
      show(`Moved ${pluralize(result.moved, "story")} out of ${sprint.name}`);
      warn(result.warnings);
      await changed();
      onClose();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal title={`Move unfinished stories out of ${sprint.name}`} onClose={onClose}>
      <p className="muted">Unfinished stories and their unfinished subtasks move. Done stories stay where they were finished.</p>
      <label className="field">
        <span>Move to</span>
        <select value={target} onChange={(event) => setTarget(event.target.value)}>
          {targets.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} ({sprintDates(item)})
            </option>
          ))}
          <option value="">Backlog</option>
        </select>
      </label>
      <FormError message={error} />
      <div className="modal-actions">
        <button className="secondary-button" onClick={onClose}>
          Cancel
        </button>
        <button onClick={move} disabled={busy}>
          Move stories
        </button>
      </div>
    </Modal>
  );
}
