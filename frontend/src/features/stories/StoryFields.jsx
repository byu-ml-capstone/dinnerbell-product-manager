import { POINTS, PRIORITIES, STATUSES } from "../../constants";
import { sprintDates } from "../../format";

/** Shared inputs for the create and edit forms. `value` is a flat form object; `onChange(key, value)`. */
export function StoryFields({ value, onChange, members, sprints, showStatus = false, sprintLocked = false, sprintHint = "" }) {
  const set = (key) => (event) => onChange(key, event.target.value);
  return (
    <div className="story-fields">
      <label className="field span-2">
        <span>Title</span>
        <input required maxLength={255} value={value.title} onChange={set("title")} />
      </label>
      <label className="field span-2">
        <span>Description</span>
        <textarea value={value.description} onChange={set("description")} />
      </label>
      <label className="field span-2">
        <span>Acceptance criteria</span>
        <textarea value={value.acceptance_criteria} onChange={set("acceptance_criteria")} placeholder="One per line" />
      </label>
      {showStatus && (
        <label className="field">
          <span>Status</span>
          <select value={value.status} onChange={set("status")}>
            {STATUSES.map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="field">
        <span>Priority</span>
        <select value={value.priority} onChange={set("priority")}>
          {PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {priority}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Points</span>
        <select value={value.story_points} onChange={set("story_points")}>
          <option value="">No points</option>
          {POINTS.map((points) => (
            <option key={points} value={points}>
              {points}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Assignee</span>
        <select value={value.assignee_id} onChange={set("assignee_id")}>
          <option value="">Unassigned</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Due date</span>
        <input type="date" value={value.due_date} onChange={set("due_date")} />
      </label>
      <label className="field">
        <span>Sprint</span>
        <select value={value.sprint_id} onChange={set("sprint_id")} disabled={sprintLocked}>
          <option value="">Backlog</option>
          {sprints.map((sprint) => (
            <option key={sprint.id} value={sprint.id}>
              {sprint.name} ({sprintDates(sprint)})
            </option>
          ))}
        </select>
        {sprintHint && <small className="muted">{sprintHint}</small>}
      </label>
      <label className="field">
        <span>Branch</span>
        <input value={value.github_branch} onChange={set("github_branch")} placeholder="name/task or a GitHub branch URL" />
      </label>
    </div>
  );
}

/** Converts form strings into API values (empty strings become null). */
export function toPayload(form) {
  return {
    title: form.title,
    description: form.description,
    acceptance_criteria: form.acceptance_criteria,
    priority: form.priority,
    story_points: form.story_points ? Number(form.story_points) : null,
    assignee_id: form.assignee_id || null,
    due_date: form.due_date || null,
    sprint_id: form.sprint_id || null,
    github_branch: form.github_branch.trim() || null,
    ...(form.status ? { status: form.status } : {}),
  };
}
