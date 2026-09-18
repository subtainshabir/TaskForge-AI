import { useCallback, useEffect, useState } from "react";
import { taskService } from "../services/taskService.js";
import { apiErrorMessage } from "../utils/apiErrorMessage.js";

export function useTasks(projectId) {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchTasks = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    setError("");
    try {
      const data = await taskService.list(projectId);
      setTasks(data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

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