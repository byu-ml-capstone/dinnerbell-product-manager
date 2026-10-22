import { get, post, put } from "./client";

export const analysesApi = {
  list: (sprintId) => get(`/sprints/${sprintId}/analyses`),
  create: (sprintId, additionalContext) => post(`/sprints/${sprintId}/analyses`, { additional_context: additionalContext }),
  get: (id) => get(`/analyses/${id}`),
  save: (id, finalContent) => put(`/analyses/${id}`, { final_content: finalContent }),
};
