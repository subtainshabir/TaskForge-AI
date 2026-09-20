import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { defaultOrderFor } from "../utils/taskFilterSort.js";

const DEFAULT_SORT = "newest";

export function useTaskFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const status = searchParams.get("status") || "";
  const priority = searchParams.get("priority") || "";
  const due = searchParams.get("due") || "";
  const search = searchParams.get("q") || "";
  const sortBy = searchParams.get("sort") || DEFAULT_SORT;
  const order = searchParams.get("order") || defaultOrderFor(sortBy);

  const setParam = useCallback(
    (key, value) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value) next.set(key, value);
          else next.delete(key);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const setSort = useCallback(
    (nextSortBy) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("sort", nextSortBy);
          next.set("order", defaultOrderFor(nextSortBy));
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const toggleOrder = useCallback(() => {
    setParam("order", order === "asc" ? "desc" : "asc");
  }, [order, setParam]);

  const clearFilters = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        ["status", "priority", "due", "q", "sort", "order"].forEach((key) => next.delete(key));
        return next;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  const hasActiveFilters = Boolean(status || priority || due || search.trim());

  return {
    status,
    priority,
    due,
    search,
    sortBy,
    order,
    setStatus: (value) => setParam("status", value),
    setPriority: (value) => setParam("priority", value),
    setDue: (value) => setParam("due", value),
    setSearch: (value) => setParam("q", value),
    setSort,
    toggleOrder,
    clearFilters,
    hasActiveFilters,
  };
}