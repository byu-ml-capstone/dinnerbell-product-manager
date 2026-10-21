import { del, get, post } from "./client";

export const dependenciesApi = {
  add: (blockerId, blockedId, reason) => post(`/stories/${blockerId}/blocks/${blockedId}`, { reason }),
  remove: (blockerId, blockedId) => del(`/stories/${blockerId}/blocks/${blockedId}`),
  graph: (projectId, { sprintId, includeDone }) =>
    get(`/projects/${projectId}/dependency-graph`, { sprint_id: sprintId, include_done: includeDone }),
};
