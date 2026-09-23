import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import AppShell from "./layouts/AppShell/AppShell.jsx";
import Dashboard from "./pages/Dashboard/Dashboard.jsx";
import LoginPage from "./pages/Login/LoginPage.jsx";
import RegisterPage from "./pages/Register/RegisterPage.jsx";
import SettingsPage from "./pages/Settings/SettingsPage.jsx";
import ProjectsPage from "./pages/Projects/ProjectsPage.jsx";
import ProjectDetailsPage from "./pages/ProjectDetails/ProjectDetailsPage.jsx";
import TaskDetailsPage from "./pages/TaskDetails/TaskDetailsPage.jsx";
import TasksPage from "./pages/Tasks/TasksPage.jsx";
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
                <Route path="/projects" element={<ProjectsPage />} />
                <Route path="/projects/:projectId" element={<ProjectDetailsPage />} />
                <Route path="/projects/:projectId/tasks" element={<ProjectDetailsPage initialSection="tasks" />} />
                <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetailsPage />} />
                <Route path="/tasks" element={<TasksPage />} />
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