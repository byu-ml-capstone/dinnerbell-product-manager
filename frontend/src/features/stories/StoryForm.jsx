import { useState } from "react";
import { Plus } from "lucide-react";
import { storiesApi } from "../../api/stories";
import { FormError } from "../../components/ErrorBanner";
import { Modal } from "../../components/Modal";
import { useToast } from "../../components/Toast";
import { useWorkspace } from "../../workspace";
import { StoryFields, toPayload } from "./StoryFields";

const EMPTY = {
  title: "",
  description: "",
  acceptance_criteria: "",
  priority: "medium",
  story_points: "",
  assignee_id: "",
  due_date: "",
  sprint_id: "",
  github_branch: "",
};

export function StoryFormButton({ label = "Story", defaultSprintId }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>
        <Plus size={16} /> {label}
      </button>
      {open && <StoryForm defaultSprintId={defaultSprintId} onClose={() => setOpen(false)} />}
    </>
  );
}

/** New story: defaults to the selected sprint unless it's closed (§6 UI changes). */
export function StoryForm({ defaultSprintId, onClose }) {
  const { project, members, sprints, selectedSprint, changed, openStory } = useWorkspace();
  const { warn } = useToast();
  const openSprints = sprints.filter((sprint) => sprint.status !== "closed");
  const initialSprint =
    defaultSprintId !== undefined ? defaultSprintId : selectedSprint && selectedSprint.status !== "closed" ? selectedSprint.id : "";
  const [form, setForm] = useState({ ...EMPTY, sprint_id: initialSprint || "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await storiesApi.create(project.id, toPayload(form));
      warn(created.warnings);
      await changed();
      openStory(created.id);
      onClose();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal title="New story" onClose={onClose} wide>
      <form onSubmit={submit}>
        <StoryFields value={form} onChange={(key, value) => setForm((current) => ({ ...current, [key]: value }))} members={members} sprints={openSprints} />
        <FormError message={error} />
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button disabled={busy}>Create story</button>
        </div>
      </form>
    </Modal>
  );
}
