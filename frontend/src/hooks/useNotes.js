import { useCallback, useEffect, useRef, useState } from "react";
import { noteService } from "../services/noteService.js";
import { apiErrorMessage } from "../utils/apiErrorMessage.js";

export function useNotes({
  projectId = null,
  taskId = null,
  generalOnly = false,
  search = "",
  sortBy = "updated_at",
  order = "desc",
} = {}) {
  const [notes, setNotes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const requestIdRef = useRef(0);

  const fetchNotes = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setIsLoading(true);
    setError("");

    try {
      let data;
      if (taskId) {
        data = await noteService.listTaskNotes(taskId);
      } else if (projectId && !search && !generalOnly && sortBy === "updated_at" && order === "desc") {
        data = await noteService.listProjectNotes(projectId);
      } else {
        const params = {};
        if (projectId) params.project_id = projectId;
        if (taskId) params.task_id = taskId;
        if (generalOnly) params.general_only = true;
        const term = (search || "").trim();
        if (term) params.search = term;
        if (sortBy) params.sort_by = sortBy;
        if (order) params.order = order;
        data = await noteService.list(params);
      }

      if (requestId !== requestIdRef.current) return;
      setNotes(data || []);
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setError(apiErrorMessage(err, "Failed to load notes."));
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [projectId, taskId, generalOnly, search, sortBy, order]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const addNote = useCallback((note) => {
    setNotes((prev) => [note, ...prev]);
  }, []);

  const replaceNote = useCallback((note) => {
    setNotes((prev) => prev.map((n) => (n.id === note.id ? note : n)));
  }, []);

  const removeNote = useCallback((noteId) => {
    setNotes((prev) => prev.filter((n) => n.id !== noteId));
  }, []);

  return {
    notes,
    isLoading,
    error,
    refetch: fetchNotes,
    addNote,
    replaceNote,
    removeNote,
    setNotes,
  };
}
