export const APP_NAME = "DinnerBell Product Manager";

export const STATUSES = [
  ["backlog", "Backlog"],
  ["selected", "Selected"],
  ["in_progress", "In Progress"],
  ["blocked", "Blocked"],
  ["done", "Done"],
];

export const STATUS_LABELS = Object.fromEntries(STATUSES);

export const PRIORITIES = ["urgent", "high", "medium", "low"];

// Fibonacci scale (CORE-5).
export const POINTS = [1, 2, 3, 5, 8, 13];

export const SPRINT_STATUS_LABELS = { planned: "Planned", active: "Active", closed: "Closed" };
