import { apiClient } from "./apiClient.js";

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export const taskService = {
  list(projectId, params = {}) {
    return apiClient.request(`/projects/${projectId}/tasks${buildQuery(params)}`);
  },

  create(projectId, payload) {
    return apiClient.request(`/projects/${projectId}/tasks`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  get(taskId) {
    return apiClient.request(`/tasks/${taskId}`);
  },

  update(taskId, payload) {
    return apiClient.request(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  remove(taskId) {
    return apiClient.request(`/tasks/${taskId}`, { method: "DELETE" });
  },
};