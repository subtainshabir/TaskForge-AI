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

  listAll(params = {}) {
    return apiClient.request(`/tasks${buildQuery(params)}`);
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

  getDependencies(taskId) {
    return apiClient.request(`/tasks/${taskId}/dependencies`);
  },

  addDependency(taskId, dependsOnTaskId) {
    return apiClient.request(`/tasks/${taskId}/dependencies`, {
      method: "POST",
      body: JSON.stringify({ depends_on_task_id: dependsOnTaskId }),
    });
  },

  removeDependency(taskId, dependencyId) {
    return apiClient.request(`/tasks/${taskId}/dependencies/${dependencyId}`, {
      method: "DELETE",
    });
  },

  getActivities(taskId, params = {}) {
    return apiClient.request(`/tasks/${taskId}/activities${buildQuery(params)}`);
  },

  analyzeWithAI(taskId) {
    return apiClient.request(`/tasks/${taskId}/ai/analyze`, {
      method: "POST",
    });
  },

  analyzePriorityWithAI(taskId) {
    return apiClient.request(`/tasks/${taskId}/ai/priority`, {
      method: "POST",
    });
  },

  analyzeQualityWithAI(taskId) {
    return apiClient.request(`/tasks/${taskId}/ai/quality`, {
      method: "POST",
    });
  },

  getPhases(taskId) {
    return apiClient.request(`/tasks/${taskId}/phases`);
  },

  createPhase(taskId, payload) {
    return apiClient.request(`/tasks/${taskId}/phases`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updatePhase(taskId, phaseId, payload) {
    return apiClient.request(`/tasks/${taskId}/phases/${phaseId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  deletePhase(taskId, phaseId) {
    return apiClient.request(`/tasks/${taskId}/phases/${phaseId}`, {
      method: "DELETE",
    });
  },

  generatePhases(taskId, replaceExisting = false) {
    return apiClient.request(`/tasks/${taskId}/phases/generate`, {
      method: "POST",
      body: JSON.stringify({ replace_existing: replaceExisting }),
    });
  },

  refinePhases(taskId) {
    return apiClient.request(`/tasks/${taskId}/phases/refine`, {
      method: "POST",
    });
  },

  applyPhaseRefinements(taskId, suggestions) {
    return apiClient.request(`/tasks/${taskId}/phases/refine/apply`, {
      method: "POST",
      body: JSON.stringify({ suggestions }),
    });
  },

  getProjectTaskSuggestions(projectId) {
    return apiClient.request(`/projects/${projectId}/ai/task-suggestions`, {
      method: "POST",
    });
  },

  applyProjectTaskSuggestions(projectId, suggestions) {
    return apiClient.request(`/projects/${projectId}/ai/task-suggestions/apply`, {
      method: "POST",
      body: JSON.stringify({ suggestions }),
    });
  },

  getTaskRelatedSuggestions(taskId) {
    return apiClient.request(`/tasks/${taskId}/ai/suggestions`, {
      method: "POST",
    });
  },

  applyTaskRelatedSuggestions(taskId, suggestions) {
    return apiClient.request(`/tasks/${taskId}/ai/suggestions/apply`, {
      method: "POST",
      body: JSON.stringify({ suggestions }),
    });
  },

  regenerateWithAI(taskId, instruction = null) {
    return apiClient.request(`/tasks/${taskId}/ai/regenerate`, {
      method: "POST",
      body: JSON.stringify({ instruction: instruction || null }),
    });
  },
};