import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiClient } from "../services/apiClient.js";
import { authService } from "../services/authService.js";

const TOKEN_STORAGE_KEY = "taskforge_access_token";

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    apiClient.setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    apiClient.setUnauthorizedHandler(clearAuth);
  }, [clearAuth]);

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!stored) {
        setIsLoading(false);
        return;
      }

      apiClient.setAuthToken(stored);
      try {
        const currentUser = await authService.me();
        if (cancelled) return;
        setUser(currentUser);
        setToken(stored);
      } catch (error) {
        if (!cancelled) clearAuth();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    initialize();
    return () => {
      cancelled = true;
    };
  }, [clearAuth]);

  const login = useCallback(async (email, password) => {
    const { access_token } = await authService.login(email, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
    apiClient.setAuthToken(access_token);
    const currentUser = await authService.me();
    setToken(access_token);
    setUser(currentUser);
    return currentUser;
  }, []);

  const register = useCallback((name, email, password) => {
    return authService.register(name, email, password);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
  }, [clearAuth]);

  const updateUser = useCallback((partialUser) => {
    setUser((previous) => (previous ? { ...previous, ...partialUser } : previous));
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user),
    isLoading,
    login,
    register,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}