import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import RequireAuth from "./components/RequireAuth";
import RequirePermission from "./components/RequirePermission";
import { CurrentUserProvider } from "./context/CurrentUserContext";
import { OdooInstanceProvider } from "./context/OdooInstanceContext";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import ConnectionPage from "./pages/ConnectionPage";
import DestinationLocationsPage from "./pages/DestinationLocationsPage";
import DriversPage from "./pages/DriversPage";
import LoadPlanningPage from "./pages/LoadPlanningPage";
import LoginPage from "./pages/LoginPage";
import OperationTypesPage from "./pages/OperationTypesPage";
import PlanningPage from "./pages/PlanningPage";
import UsersPage from "./pages/UsersPage";
import VehiclesPage from "./pages/VehiclesPage";
import WarehousesPage from "./pages/WarehousesPage";

export default function App() {
  return (
    <OdooInstanceProvider>
      <CurrentUserProvider>
        <NavBar />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/connection"
            element={
              <RequireAuth>
                <RequirePermission permission="can_manage_connection">
                  <ConnectionPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/operation-types"
            element={
              <RequireAuth>
                <RequirePermission permission="can_manage_operation_types">
                  <OperationTypesPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/warehouses"
            element={
              <RequireAuth>
                <RequirePermission permission="can_manage_warehouses">
                  <WarehousesPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/destinations"
            element={
              <RequireAuth>
                <RequirePermission permission="can_manage_warehouses">
                  <DestinationLocationsPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/vehicles"
            element={
              <RequireAuth>
                <RequirePermission permission="can_manage_fleet">
                  <VehiclesPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/drivers"
            element={
              <RequireAuth>
                <RequirePermission permission="can_manage_fleet">
                  <DriversPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/planning"
            element={
              <RequireAuth>
                <RequirePermission permission="can_run_planning">
                  <PlanningPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/load-planning"
            element={
              <RequireAuth>
                <RequirePermission permission="can_use_load_planning">
                  <LoadPlanningPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/users"
            element={
              <RequireAuth>
                <RequirePermission adminOnly>
                  <UsersPage />
                </RequirePermission>
              </RequireAuth>
            }
          />
          <Route
            path="/account"
            element={
              <RequireAuth>
                <ChangePasswordPage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/planning" replace />} />
        </Routes>
      </CurrentUserProvider>
    </OdooInstanceProvider>
  );
}
