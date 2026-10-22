import { get } from "./client";

export const metricsApi = {
  velocity: (projectId) => get(`/projects/${projectId}/velocity`),
  sprint: (sprintId) => get(`/sprints/${sprintId}/metrics`),
};
