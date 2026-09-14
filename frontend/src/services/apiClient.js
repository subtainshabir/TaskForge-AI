const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

let authToken = null;
let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function extractErrorMessage(data) {
  if (!data) return null;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return data.detail[0]?.msg || null;
  }
  return null;
}

function setAuthToken(token) {
  authToken = token;
}

function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch (networkError) {
    throw new ApiError("Unable to connect to the server. Please try again.", 0);
  }

  if (response.status === 401 && authToken) {
    unauthorizedHandler?.();
  }

  if (!response.ok) {
    let data = null;
    try {
      data = await response.json();
    } catch (parseError) {
      data = null;
    }
    throw new ApiError(
      extractErrorMessage(data) || "Something went wrong. Please try again.",
      response.status
    );
  }

  if (response.status === 204) return null;
  return response.json();
}

export const apiClient = { request, setAuthToken, setUnauthorizedHandler };