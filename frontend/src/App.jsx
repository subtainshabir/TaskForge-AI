import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import AppShell from "./layouts/AppShell/AppShell.jsx";
import Dashboard from "./pages/Dashboard/Dashboard.jsx";
import LoginPage from "./pages/Login/LoginPage.jsx";
import RegisterPage from "./pages/Register/RegisterPage.jsx";
import SettingsPage from "./pages/Settings/SettingsPage.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";
import PublicOnlyRoute from "./routes/PublicOnlyRoute.jsx";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route index element={<Dashboard />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Route>
          </Routes>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;