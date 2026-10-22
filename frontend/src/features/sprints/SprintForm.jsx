import { useState } from "react";
import { sprintsApi } from "../../api/sprints";
import { FormError } from "../../components/ErrorBanner";
import { Modal } from "../../components/Modal";
import { addDays, formatDate, isoDate } from "../../format";
import { useWorkspace } from "../../workspace";

/** Creating a sprint looks the same for every sprint; a future start date makes it planned (D-29). */
export function SprintForm({ sprint = null, onClose, onSaved }) {
  const { project } = useWorkspace();
  const today = isoDate(new Date());
  const [form, setForm] = useState(() =>
    sprint
      ? { name: sprint.name, goal: sprint.goal, start_date: sprint.start_date, end_date: sprint.end_date }
      : { name: "", goal: "", start_date: today, end_date: addDays(today, 13) },
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (event) => {
    const value = event.target.value;
    setForm((current) => ({ ...current, [key]: value }));
  };

  async function submit(event) {
    event.preventDefault();
    if (form.end_date < form.start_date) {
      setError("The end date must be on or after the start date.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = { ...form, name: form.name.trim() || undefined };
      const saved = sprint ? await sprintsApi.update(sprint.id, payload) : await sprintsApi.create(project.id, payload);
      await onSaved(saved);
      onClose();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal title={sprint ? `Edit ${sprint.name}` : "New sprint"} onClose={onClose}>
      <form className="stack-form" onSubmit={submit}>
        <label className="field">
          <span>Name</span>
          <input value={form.name} onChange={set("name")} placeholder={sprint ? "" : "Leave blank for “Sprint N”"} />
        </label>
        <label className="field">
          <span>Goal</span>
          <textarea value={form.goal} onChange={set("goal")} />
        </label>
        <div className="two-columns">
          <label className="field">
            <span>Start date</span>
            <input
              type="date"
              required
              value={form.start_date}
              onChange={(event) => {
                const start = event.target.value;
                setForm((current) => ({
                  ...current,
                  start_date: start,
                  end_date: current.end_date < start ? addDays(start, 13) : current.end_date,
                }));
              }}
            />
          </label>
          <label className="field">
            <span>End date</span>
            <input type="date" required min={form.start_date} value={form.end_date} onChange={set("end_date")} />
          </label>
        </div>
        {form.start_date > today && <p className="muted">Planned. Starts {formatDate(form.start_date)}.</p>}
        <FormError message={error} />
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button disabled={busy}>{sprint ? "Save" : "Create sprint"}</button>
        </div>
      </form>
    </Modal>
  );
}
