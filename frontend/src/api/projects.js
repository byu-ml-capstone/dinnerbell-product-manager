import { del, get, post, put } from "./client";

export const projectsApi = {
  list: () => get("/projects"),
  create: (payload) => post("/projects", payload),
  get: (id) => get(`/projects/${id}`),
  update: (id, payload) => put(`/projects/${id}`, payload),
  remove: (id) => del(`/projects/${id}`),
  addMember: (id, userId) => post(`/projects/${id}/team`, { user_id: userId }),
  removeMember: (id, userId) => del(`/projects/${id}/team/${userId}`),
  summary: (id) => get(`/projects/${id}/summary`),
  planning: (id) => get(`/projects/${id}/planning`),
};
