import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import RequireAuth from "./components/RequireAuth";
import ConnectionPage from "./pages/ConnectionPage";
import LoginPage from "./pages/LoginPage";
import OperationTypesPage from "./pages/OperationTypesPage";
import PlanningPage from "./pages/PlanningPage";
import WarehousesPage from "./pages/WarehousesPage";

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
          path="/operation-types"
          element={
            <RequireAuth>
              <OperationTypesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/warehouses"
          element={
            <RequireAuth>
              <WarehousesPage />
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
