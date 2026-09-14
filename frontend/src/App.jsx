import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppShell from "./layouts/AppShell/AppShell.jsx";
import Dashboard from "./pages/DashBoard/Dashboard.jsx";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;