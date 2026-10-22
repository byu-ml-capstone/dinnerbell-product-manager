import { SPRINT_STATUS_LABELS } from "../../constants";
import { sprintDates } from "../../format";
import { useWorkspace } from "../../workspace";

export function sprintBadge(sprint) {
  if (sprint.is_overdue) return "Overdue";
  return SPRINT_STATUS_LABELS[sprint.status] || sprint.status;
}

export function SprintBadge({ sprint }) {
  const label = sprintBadge(sprint);
  return <span className={`sprint-badge ${label.toLowerCase()}`}>{label}</span>;
}

export function SprintPicker({ label = "Selected sprint" }) {
  const { sprints, selectedSprint, selectSprint } = useWorkspace();
  if (!sprints.length) return null;
  return (
    <label className="field">
      <span>{label}</span>
      <select value={selectedSprint?.id || ""} onChange={(event) => selectSprint(event.target.value)}>
        {sprints.map((sprint) => (
          <option key={sprint.id} value={sprint.id}>
            {sprint.name} · {sprintBadge(sprint)} · {sprintDates(sprint)}
          </option>
        ))}
      </select>
    </label>
  );
}
