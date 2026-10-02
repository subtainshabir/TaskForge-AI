import { apiClient } from "./apiClient.js";

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export const noteService = {
  list(params = {}) {
    return apiClient.request(`/notes${buildQuery(params)}`);
  },

  get(noteId) {
    return apiClient.request(`/notes/${noteId}`);
  },

  create(payload) {
    return apiClient.request("/notes", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(noteId, payload) {
    return apiClient.request(`/notes/${noteId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  remove(noteId) {
    return apiClient.request(`/notes/${noteId}`, {
      method: "DELETE",
    });
  },

  listProjectNotes(projectId) {
    return apiClient.request(`/projects/${projectId}/notes`);
  },

  listTaskNotes(taskId) {
    return apiClient.request(`/tasks/${taskId}/notes`);
  },

  summarizeWithAI(noteId) {
    return apiClient.request(`/notes/${noteId}/ai/summarize`, {
      method: "POST",
    });
  },

  extractWithAI(noteId) {
    return apiClient.request(`/notes/${noteId}/ai/extract`, {
      method: "POST",
    });
  },

  suggestTasksWithAI(noteId) {
    return apiClient.request(`/notes/${noteId}/ai/task-suggestions`, {
      method: "POST",
    });
  },

  improveWithAI(noteId) {
    return apiClient.request(`/notes/${noteId}/ai/improve`, {
      method: "POST",
    });
  },
};
