import { apiClient } from "./apiClient.js";

export const userService = {
  getProfile() {
    return apiClient.request("/users/me");
  },

  updateProfile(name) {
    return apiClient.request("/users/me", {
      method: "PATCH",
      body: JSON.stringify({ name }),
    });
  },

  getSettings() {
    return apiClient.request("/users/me/settings");
  },

  updateSettings(partialSettings) {
    return apiClient.request("/users/me/settings", {
      method: "PATCH",
      body: JSON.stringify(partialSettings),
    });
  },
};