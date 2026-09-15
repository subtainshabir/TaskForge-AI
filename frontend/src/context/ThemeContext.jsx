import { createContext, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext.jsx";
import { userService } from "../services/userService.js";

const THEME_CACHE_KEY = "taskforge_theme_preference";

const ThemeContext = createContext(undefined);

function resolveSystemTheme() {
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(preference) {
  const resolved = preference === "system" ? resolveSystemTheme() : preference;
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", resolved);
  }
  return resolved;
}

export function ThemeProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [preference, setPreference] = useState(
    () => localStorage.getItem(THEME_CACHE_KEY) || "system"
  );
  const [resolvedTheme, setResolvedTheme] = useState(() => applyTheme(preference));

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    let cancelled = false;

    userService
      .getSettings()
      .then((data) => {
        if (cancelled) return;
        setPreference(data.theme);
        setResolvedTheme(applyTheme(data.theme));
        localStorage.setItem(THEME_CACHE_KEY, data.theme);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    if (preference !== "system" || !window.matchMedia) return undefined;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => setResolvedTheme(applyTheme("system"));
    mql.addEventListener("change", handleChange);
    return () => mql.removeEventListener("change", handleChange);
  }, [preference]);

  async function setTheme(next) {
    const previous = preference;
    setPreference(next);
    setResolvedTheme(applyTheme(next));
    localStorage.setItem(THEME_CACHE_KEY, next);

    try {
      await userService.updateSettings({ theme: next });
    } catch (error) {
      setPreference(previous);
      setResolvedTheme(applyTheme(previous));
      localStorage.setItem(THEME_CACHE_KEY, previous);
      throw error;
    }
  }

  const value = { theme: preference, resolvedTheme, setTheme };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}