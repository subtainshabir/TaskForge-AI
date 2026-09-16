import { useCallback, useEffect, useState } from "react";
import { projectService } from "../services/projectService.js";
import { apiErrorMessage } from "../utils/apiErrorMessage.js";

export function useProjects() {
  const [projects, setProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await projectService.list({ sort_by: "updated_at", order: "desc" });
      setProjects(data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const addProject = useCallback((project) => {
    setProjects((previous) => [project, ...previous]);
  }, []);

  const replaceProject = useCallback((project) => {
    setProjects((previous) => previous.map((p) => (p.id === project.id ? project : p)));
  }, []);

  const removeProject = useCallback((projectId) => {
    setProjects((previous) => previous.filter((p) => p.id !== projectId));
  }, []);

  return {
    projects,
    isLoading,
    error,
    refetch: fetchProjects,
    addProject,
    replaceProject,
    removeProject,
  };
}