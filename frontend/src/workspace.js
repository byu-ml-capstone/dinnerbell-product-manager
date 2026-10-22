import { createContext, useContext } from "react";

/**
 * What every view needs about the current project: the user, project, members, sprints, the selected
 * sprint, a `version` that bumps after any change, and helpers to open the story drawer.
 */
export const WorkspaceContext = createContext(null);

export function useWorkspace() {
  return useContext(WorkspaceContext);
}

/** localStorage can throw (private windows, blocked storage); it's only a convenience here. */
export const storage = {
  get(key) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      if (value === null || value === undefined || value === "") window.localStorage.removeItem(key);
      else window.localStorage.setItem(key, value);
    } catch {
      // ignore
    }
  },
};

/** Active sprint with the earliest start, else the next planned one, else the most recently closed (§6 UI). */
export function defaultSprint(sprints) {
  const byStart = [...sprints].sort((a, b) => a.start_date.localeCompare(b.start_date));
  return (
    byStart.find((sprint) => sprint.status === "active") ||
    byStart.find((sprint) => sprint.status === "planned") ||
    sprints.filter((sprint) => sprint.status === "closed").sort((a, b) => (b.closed_at || "").localeCompare(a.closed_at || ""))[0] ||
    null
  );
}
