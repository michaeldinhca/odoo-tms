import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import RequireAuth from "./components/RequireAuth";
import ConnectionPage from "./pages/ConnectionPage";
import LoginPage from "./pages/LoginPage";
import PlanningPage from "./pages/PlanningPage";

export default function App() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/connection"
          element={
            <RequireAuth>
              <ConnectionPage />
            </RequireAuth>
          }
        />
        <Route
          path="/planning"
          element={
            <RequireAuth>
              <PlanningPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/planning" replace />} />
      </Routes>
    </>
  );
}
