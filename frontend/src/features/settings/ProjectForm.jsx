import { useState } from "react";
import { Plus } from "lucide-react";
import { FormError } from "../../components/ErrorBanner";

export function ProjectForm({ users, onCreate }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");

  if (!open) {
    return (
      <button className="wide-button" onClick={() => setOpen(true)}>
        <Plus size={16} /> New Project
      </button>
    );
  }
  return (
    <form
      className="stack-form"
      onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try {
          await onCreate({ name, description, team_member_ids: members });
          setOpen(false);
          setName("");
          setDescription("");
          setMembers([]);
        } catch (err) {
          setError(err.message);
        }
      }}
    >
      <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Project name" aria-label="Project name" />
      <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Description" aria-label="Description" />
      {users.length > 0 && (
        <label className="field">
          <span>Team members</span>
          <select
            multiple
            value={members}
            onChange={(event) => setMembers(Array.from(event.target.selectedOptions).map((option) => option.value))}
          >
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name} (@{user.username})
              </option>
            ))}
          </select>
        </label>
      )}
      <FormError message={error} />
      <div className="button-row">
        <button type="button" className="secondary-button" onClick={() => setOpen(false)}>
          Cancel
        </button>
        <button>Create</button>
      </div>
    </form>
  );
}
