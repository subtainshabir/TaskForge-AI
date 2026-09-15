import { apiClient } from "./apiClient.js";

export const authService = {
  register(name, email, password) {
    return apiClient.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
  },

  login(email, password) {
    return apiClient.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  me() {
    return apiClient.request("/auth/me");
  },
};