import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import RequireAuth from "./components/RequireAuth";
import { OdooInstanceProvider } from "./context/OdooInstanceContext";
import ConnectionPage from "./pages/ConnectionPage";
import DriversPage from "./pages/DriversPage";
import LoginPage from "./pages/LoginPage";
import OperationTypesPage from "./pages/OperationTypesPage";
import PlanningPage from "./pages/PlanningPage";
import VehiclesPage from "./pages/VehiclesPage";
import WarehousesPage from "./pages/WarehousesPage";

export default function App() {
  return (
    <OdooInstanceProvider>
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
          path="/vehicles"
          element={
            <RequireAuth>
              <VehiclesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/drivers"
          element={
            <RequireAuth>
              <DriversPage />
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
    </OdooInstanceProvider>
  );
}
