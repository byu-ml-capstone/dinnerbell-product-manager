import { get, getBlob, post, put } from "./client";

export const analysesApi = {
  list: (sprintId) => get(`/sprints/${sprintId}/analyses`),
  create: (sprintId, additionalContext, reportContext = {}) => post(`/sprints/${sprintId}/analyses`, { additional_context: additionalContext, ...reportContext }),
  get: (id) => get(`/analyses/${id}`),
  save: (id, finalContent) => put(`/analyses/${id}`, { final_content: finalContent }),
  downloadSprintReport: (id) => getBlob(`/analyses/${id}/sprint-report.pptx`),
};
