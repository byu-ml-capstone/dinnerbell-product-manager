import { del, get, post, put } from "./client";

export const sprintsApi = {
  list: (projectId) => get(`/projects/${projectId}/sprints`),
  create: (projectId, payload) => post(`/projects/${projectId}/sprints`, payload),
  get: (id) => get(`/sprints/${id}`),
  update: (id, payload) => put(`/sprints/${id}`, payload),
  remove: (id) => del(`/sprints/${id}`),
  board: (id) => get(`/sprints/${id}/board`),
  close: (id, notes) => post(`/sprints/${id}/close`, { notes }),
  moveUnfinished: (id, targetSprintId) => post(`/sprints/${id}/move-unfinished`, { target_sprint_id: targetSprintId }),
};
