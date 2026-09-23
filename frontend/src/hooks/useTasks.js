import { useCallback, useEffect, useRef, useState } from "react";
import { taskService } from "../services/taskService.js";
import { apiErrorMessage } from "../utils/apiErrorMessage.js";

export function useTasks(projectId = null, search = "") {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const requestIdRef = useRef(0);

  const fetchTasks = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    setError("");
    try {
      const params = {};
      const term = search.trim();
      if (term) params.search = term;
      const data = projectId
        ? await taskService.list(projectId, params)
        : await taskService.listAll(params);
      if (requestId !== requestIdRef.current) return;
      setTasks(data);
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setError(apiErrorMessage(err));
    } finally {
      if (requestId === requestIdRef.current) setIsLoading(false);
    }
  }, [projectId, search]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const addTask = useCallback((task) => {
    setTasks((previous) => [task, ...previous]);
  }, []);

  const replaceTask = useCallback((task) => {
    setTasks((previous) => previous.map((t) => (t.id === task.id ? task : t)));
  }, []);

  const removeTask = useCallback((taskId) => {
    setTasks((previous) => previous.filter((t) => t.id !== taskId));
  }, []);

  return { tasks, isLoading, error, refetch: fetchTasks, addTask, replaceTask, removeTask };
}