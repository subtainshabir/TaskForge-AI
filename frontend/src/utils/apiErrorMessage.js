import { ApiError } from "../services/apiClient.js";

export function apiErrorMessage(error, notFoundMessage = "Not found.") {
  if (error instanceof ApiError) {
    if (error.status === 0) return "Unable to connect to the server. Please try again.";
    if (error.status === 404) return notFoundMessage;
    if (error.status === 401) return "Your session has expired. Please sign in again.";
    return error.message || "Something went wrong. Please try again.";
  }
  return "Something went wrong. Please try again.";
}