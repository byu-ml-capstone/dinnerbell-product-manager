import { del, get, post, put } from "./client";

export const storiesApi = {
  list: (projectId) => get(`/projects/${projectId}/stories`),
  create: (projectId, payload) => post(`/projects/${projectId}/stories`, payload),
  get: (id) => get(`/stories/${id}`),
  update: (id, payload) => put(`/stories/${id}`, payload),
  remove: (id) => del(`/stories/${id}`),
  createSubtask: (id, payload) => post(`/stories/${id}/subtasks`, payload),
  addComment: (id, text) => post(`/stories/${id}/comments`, { text }),
  move: (projectId, storyIds, sprintId) => post(`/projects/${projectId}/stories/move`, { story_ids: storyIds, sprint_id: sprintId }),
  github: (id) => get(`/stories/${id}/github`),
};
