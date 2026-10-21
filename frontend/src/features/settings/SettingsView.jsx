import { useEffect, useState } from "react";
import { GitBranch, Save, Settings, Trash2, UserMinus, UserPlus, Users } from "lucide-react";
import { projectsApi } from "../../api/projects";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { useToast } from "../../components/Toast";
import { useUndoDelete } from "../../components/useUndoDelete";
import { useWorkspace } from "../../workspace";

function projectForm(project) {
  return { name: project.name, description: project.description || "", github_repo_url: project.github_repo_url || "" };
}

export function SettingsView({ onProjectDeleted }) {
  const { project, members, users, user, changed, reloadProjects } = useWorkspace();
  const { show } = useToast();
  const undoDelete = useUndoDelete();
  const [form, setForm] = useState(() => projectForm(project));
  const [error, setError] = useState("");
  const [memberError, setMemberError] = useState("");
  const [newMember, setNewMember] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Reset only when switching projects, so a reload mid-edit doesn't wipe what's being typed.
  useEffect(() => {
    setForm(projectForm(project));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);
  const set = (key) => (event) => {
    const value = event.target.value;
    setForm((current) => ({ ...current, [key]: value }));
  };

  const memberIds = new Set(members.map((member) => member.id));
  const candidates = users.filter((item) => !memberIds.has(item.id));

  async function save(event) {
    event.preventDefault();
    setError("");
    try {
      await projectsApi.update(project.id, { ...form, github_repo_url: form.github_repo_url.trim() || null });
      show("Project settings saved");
      await Promise.all([changed(), reloadProjects()]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function memberAction(action) {
    setMemberError("");
    try {
      await action();
      await Promise.all([changed(), reloadProjects()]);
    } catch (err) {
      setMemberError(err.message);
    }
  }

  return (
    <div className="settings-grid">
      <section className="panel">
        <PanelTitle icon={<Settings size={16} />} title="Project" />
        <form className="stack-form" onSubmit={save}>
          <label className="field">
            <span>Name</span>
            <input required value={form.name} onChange={set("name")} />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea value={form.description} onChange={set("description")} />
          </label>
          <label className="field">
            <span>
              <GitBranch size={12} /> GitHub repository
            </span>
            <input
              value={form.github_repo_url}
              placeholder="https://github.com/<owner>/<repo>"
              onChange={set("github_repo_url")}
            />
          </label>
          <p className="muted">Story branches link into this repository, and the sprint review reads code from it.</p>
          <FormError message={error} />
          <button>
            <Save size={16} /> Save
          </button>
        </form>
      </section>

      <section className="panel">
        <PanelTitle icon={<Users size={16} />} title="Members" />
        <ul className="member-list">
          {members.map((member) => (
            <li key={member.id}>
              <span>
                <strong>{member.name}</strong> <span className="muted">@{member.username}</span>
              </span>
              <button
                className="secondary-button compact"
                title={member.id === user.id ? "Leave this project" : "Remove from project"}
                onClick={() => memberAction(() => projectsApi.removeMember(project.id, member.id))}
              >
                <UserMinus size={14} /> {member.id === user.id ? "Leave" : "Remove"}
              </button>
            </li>
          ))}
        </ul>
        <p className="muted">Removing someone unassigns their stories. Their comments and history stay.</p>
        {candidates.length > 0 && (
          <div className="inline-form">
            <select value={newMember} onChange={(event) => setNewMember(event.target.value)} aria-label="Add member">
              <option value="">Add member</option>
              {candidates.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} (@{item.username})
                </option>
              ))}
            </select>
            <button
              disabled={!newMember}
              onClick={() =>
                memberAction(async () => {
                  await projectsApi.addMember(project.id, newMember);
                  setNewMember("");
                })
              }
            >
              <UserPlus size={15} /> Add
            </button>
          </div>
        )}
        <FormError message={memberError} />
      </section>

      <section className="panel danger-zone">
        <PanelTitle icon={<Trash2 size={16} />} title="Danger zone" />
        <p className="muted">Deleting the project hides it and everything in it. It can be restored from "Deleted projects" in the sidebar.</p>
        <button className="danger-button" onClick={() => setConfirmDelete(true)}>
          <Trash2 size={16} /> Delete project
        </button>
      </section>

      {confirmDelete && (
        <ConfirmDialog
          title="Delete project?"
          body={
            <p>
              This deletes <strong>{project.name}</strong> with all of its sprints, stories, comments and discussion. You can restore
              it later.
            </p>
          }
          confirmLabel="Delete project"
          danger
          onCancel={() => setConfirmDelete(false)}
          onConfirm={async () => {
            const result = await projectsApi.remove(project.id);
            setConfirmDelete(false);
            const name = project.name;
            await onProjectDeleted();
            undoDelete(name, result, reloadProjects);
          }}
        />
      )}
    </div>
  );
}
