import { del, get, post, put } from "./client";

export const messagesApi = {
  list: (sprintId, since) => get(`/sprints/${sprintId}/messages`, { since }),
  create: (sprintId, text, parentMessageId = null) => post(`/sprints/${sprintId}/messages`, { text, parent_message_id: parentMessageId }),
  update: (id, text) => put(`/sprint-messages/${id}`, { text }),
  remove: (id) => del(`/sprint-messages/${id}`),
};
