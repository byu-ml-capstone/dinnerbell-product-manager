import { get, post } from "./client";

export const trashApi = {
  project: (projectId) => get(`/projects/${projectId}/trash`),
  deletedProjects: () => get("/trash/projects"),
  restore: (batchId) => post(`/trash/${batchId}/restore`),
};
