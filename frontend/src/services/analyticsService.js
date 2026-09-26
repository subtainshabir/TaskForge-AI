import { apiClient } from "./apiClient.js";

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export const analyticsService = {
  getProgress(params = {}) {
    return apiClient.request(`/analytics/progress${buildQuery(params)}`);
  },

  getInsights(params = {}) {
    return apiClient.request(`/analytics/progress/insights${buildQuery(params)}`, {
      method: "POST",
    });
  },
};
