import { get, post } from "./client";

export const reviewsApi = {
  list: (sprintId) => get(`/sprints/${sprintId}/reviews`),
  start: (sprintId) => post(`/sprints/${sprintId}/reviews`),
  get: (id) => get(`/reviews/${id}`),
};
