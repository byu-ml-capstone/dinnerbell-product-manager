import { useState } from "react";
import { storiesApi } from "../../api/stories";
import { FormError } from "../../components/ErrorBanner";
import { useToast } from "../../components/Toast";
import { sprintDates } from "../../format";
import { useWorkspace } from "../../workspace";
import { StoryFields, toPayload } from "./StoryFields";

function toForm(story) {
  return {
    title: story.title,
    description: story.description || "",
    acceptance_criteria: story.acceptance_criteria || "",
    status: story.status,
    priority: story.priority,
    story_points: story.story_points ? String(story.story_points) : "",
    assignee_id: story.assignee_id || "",
    due_date: story.due_date || "",
    sprint_id: story.sprint_id || "",
    github_branch: story.github_branch || "",
  };
}

/** Edits every field (CORE-10). Only changed fields are sent, so unrelated rules aren't triggered. */
export function StoryEditForm({ story, onDone }) {
  const { members, sprints, changed } = useWorkspace();
  const { warn } = useToast();
  const [form, setForm] = useState(() => toForm(story));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const sprintChoices = sprints.filter((sprint) => sprint.status !== "closed" || sprint.id === story.sprint_id);
  const isSubtask = Boolean(story.parent_story_id);

  async function submit(event) {
    event.preventDefault();
    const original = toPayload(toForm(story));
    const next = toPayload(form);
    const payload = Object.fromEntries(Object.entries(next).filter(([key, value]) => value !== original[key]));
    if (Object.keys(payload).length === 0) {
      onDone();
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await storiesApi.update(story.id, payload);
      warn(result.warnings);
      await changed();
      onDone();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <form className="edit-form" onSubmit={submit}>
      <StoryFields
        value={form}
        onChange={(key, value) => setForm((current) => ({ ...current, [key]: value }))}
        members={members}
        sprints={sprintChoices}
        showStatus
        sprintLocked={isSubtask}
        sprintHint={isSubtask ? "Moves with parent" : ""}
      />
      <FormError message={error} />
      <div className="button-row">
        <button type="button" className="secondary-button" onClick={onDone}>
          Cancel
        </button>
        <button disabled={busy}>Save</button>
      </div>
    </form>
  );
}

/** A story in a closed sprint is read-only; an unfinished one can only be moved out (CORE-10, MOVE-2). */
export function MoveOutForm({ story, onDone }) {
  const { sprints, changed } = useWorkspace();
  const { warn } = useToast();
  const targets = sprints.filter((sprint) => sprint.status !== "closed");
  const [target, setTarget] = useState(targets[0]?.id || "");
  const [error, setError] = useState("");

  async function move(event) {
    event.preventDefault();
    setError("");
    try {
      const result = await storiesApi.update(story.id, { sprint_id: target || null });
      warn(result.warnings);
      await changed();
      onDone();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="stack-form" onSubmit={move}>
      <label className="field">
        <span>Move to</span>
        <select value={target} onChange={(event) => setTarget(event.target.value)}>
          {targets.map((sprint) => (
            <option key={sprint.id} value={sprint.id}>
              {sprint.name} ({sprintDates(sprint)})
            </option>
          ))}
          <option value="">Backlog</option>
        </select>
      </label>
      <FormError message={error} />
      <div className="button-row">
        <button type="button" className="secondary-button" onClick={onDone}>
          Cancel
        </button>
        <button>Move story</button>
      </div>
    </form>
  );
}
