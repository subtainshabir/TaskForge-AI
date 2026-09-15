import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import AuthLoadingScreen from "../components/AuthLoadingScreen/AuthLoadingScreen.jsx";

function PublicOnlyRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <AuthLoadingScreen />;

  if (isAuthenticated) return <Navigate to="/" replace />;

  return <Outlet />;
}

export default PublicOnlyRoute;