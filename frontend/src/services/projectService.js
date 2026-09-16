import { apiClient } from "./apiClient.js";

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export const projectService = {
  list(params = {}) {
    return apiClient.request(`/projects${buildQuery(params)}`);
  },

  create(payload) {
    return apiClient.request("/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  get(projectId) {
    return apiClient.request(`/projects/${projectId}`);
  },

  update(projectId, payload) {
    return apiClient.request(`/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  remove(projectId) {
    return apiClient.request(`/projects/${projectId}`, { method: "DELETE" });
  },
};