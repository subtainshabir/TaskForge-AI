import { createContext, useContext } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const value = {};
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  return useContext(AppContext);
}