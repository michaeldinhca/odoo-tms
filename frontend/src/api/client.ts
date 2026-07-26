import type {
  AdminPasswordResetInput,
  Driver,
  DriverInput,
  FleetVehicle,
  FleetVehicleInput,
  OdooCompany,
  OdooCredential,
  OdooCredentialTestResult,
  OdooCredentialUpsert,
  OdooEmployeeList,
  OdooFleetVehicleList,
  OperationType,
  OperationTypeRefreshPreview,
  PlanningRunResult,
  SelfPasswordChangeInput,
  TokenResponse,
  User,
  UserCreateInput,
  UserUpdateInput,
  Warehouse,
  WarehouseRefreshPreview,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

const TOKEN_KEY = "odoo_tms_token";
const TENANT_ID_KEY = "odoo_tms_tenant_id";

export function saveSession(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  const tenantId = decodeTenantId(token);
  if (tenantId) localStorage.setItem(TENANT_ID_KEY, tenantId);
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TENANT_ID_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getTenantId(): string | null {
  return localStorage.getItem(TENANT_ID_KEY);
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return null;
  }
}

function decodeTenantId(token: string): string | null {
  const payload = decodeJwtPayload(token);
  return (payload?.tenant_id as string | undefined) ?? null;
}

/** Whether a token is present *and* its `exp` claim hasn't passed yet — a
 * present-but-expired token is treated the same as no token at all, so
 * callers don't render a page that's guaranteed to fail every API call. */
export function hasValidSession(): boolean {
  const token = getToken();
  if (!token) return false;
  const exp = decodeJwtPayload(token)?.exp as number | undefined;
  if (typeof exp !== "number") return false;
  return Date.now() < exp * 1000;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401 && path !== "/auth/login") {
    // The session was rejected server-side for a reason the client-side
    // exp check above couldn't have caught (e.g. JWT_SECRET rotated,
    // token tampered with). Bounce to login rather than let every caller
    // treat this the same as "nothing saved yet" — see DECISIONS.md.
    clearSession();
    window.location.href = "/login";
    throw new ApiError(401, "Session expired — redirecting to login");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getCredential(tenantId: string): Promise<OdooCredential> {
  return request<OdooCredential>(`/tenants/${tenantId}/credentials`);
}

export function upsertCredential(
  tenantId: string,
  payload: OdooCredentialUpsert,
): Promise<OdooCredential> {
  return request<OdooCredential>(`/tenants/${tenantId}/credentials`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function reauthenticateCredential(
  tenantId: string,
  payload: OdooCredentialUpsert,
): Promise<OdooCredential> {
  return request<OdooCredential>(`/tenants/${tenantId}/credentials/reauthenticate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testCredential(tenantId: string): Promise<OdooCredentialTestResult> {
  return request<OdooCredentialTestResult>(`/tenants/${tenantId}/credentials/test`, {
    method: "POST",
  });
}

export function listCompanies(tenantId: string): Promise<OdooCompany[]> {
  return request<OdooCompany[]>(`/tenants/${tenantId}/credentials/companies`);
}

export function selectCompany(
  tenantId: string,
  companyId: number | null,
  companyName: string | null,
): Promise<OdooCredential> {
  return request<OdooCredential>(`/tenants/${tenantId}/credentials/company`, {
    method: "PUT",
    body: JSON.stringify({ company_id: companyId, company_name: companyName }),
  });
}

export function runPlanning(tenantId: string): Promise<PlanningRunResult> {
  return request<PlanningRunResult>("/planning/run", {
    method: "POST",
    body: JSON.stringify({ tenant_id: tenantId }),
  });
}

export function listOperationTypes(
  tenantId: string,
  includeArchived = false,
): Promise<OperationType[]> {
  return request<OperationType[]>(
    `/tenants/${tenantId}/operation-types?include_archived=${includeArchived}`,
  );
}

export function previewOperationTypesRefresh(
  tenantId: string,
): Promise<OperationTypeRefreshPreview> {
  return request<OperationTypeRefreshPreview>(
    `/tenants/${tenantId}/operation-types/refresh/preview`,
    { method: "POST" },
  );
}

export function refreshOperationTypes(tenantId: string): Promise<OperationType[]> {
  return request<OperationType[]>(`/tenants/${tenantId}/operation-types/refresh`, {
    method: "POST",
  });
}

export function setOperationTypeSync(
  tenantId: string,
  operationTypeId: string,
  isSynced: boolean,
): Promise<OperationType> {
  return request<OperationType>(`/tenants/${tenantId}/operation-types/${operationTypeId}/sync`, {
    method: "PUT",
    body: JSON.stringify({ is_synced: isSynced }),
  });
}

export function setOperationTypeActive(
  tenantId: string,
  operationTypeId: string,
  active: boolean,
): Promise<OperationType> {
  return request<OperationType>(
    `/tenants/${tenantId}/operation-types/${operationTypeId}/archive`,
    { method: "PUT", body: JSON.stringify({ active }) },
  );
}

export function deleteOperationType(tenantId: string, operationTypeId: string): Promise<void> {
  return request<void>(`/tenants/${tenantId}/operation-types/${operationTypeId}`, {
    method: "DELETE",
  });
}

export function listWarehouses(tenantId: string, includeArchived = false): Promise<Warehouse[]> {
  return request<Warehouse[]>(`/tenants/${tenantId}/warehouses?include_archived=${includeArchived}`);
}

export function previewWarehousesRefresh(tenantId: string): Promise<WarehouseRefreshPreview> {
  return request<WarehouseRefreshPreview>(`/tenants/${tenantId}/warehouses/refresh/preview`, {
    method: "POST",
  });
}

export function refreshWarehouses(tenantId: string): Promise<Warehouse[]> {
  return request<Warehouse[]>(`/tenants/${tenantId}/warehouses/refresh`, {
    method: "POST",
  });
}

export function setWarehouseSync(
  tenantId: string,
  warehouseId: string,
  isSynced: boolean,
): Promise<Warehouse> {
  return request<Warehouse>(`/tenants/${tenantId}/warehouses/${warehouseId}/sync`, {
    method: "PUT",
    body: JSON.stringify({ is_synced: isSynced }),
  });
}

export function setWarehouseActive(
  tenantId: string,
  warehouseId: string,
  active: boolean,
): Promise<Warehouse> {
  return request<Warehouse>(`/tenants/${tenantId}/warehouses/${warehouseId}/archive`, {
    method: "PUT",
    body: JSON.stringify({ active }),
  });
}

export function deleteWarehouse(tenantId: string, warehouseId: string): Promise<void> {
  return request<void>(`/tenants/${tenantId}/warehouses/${warehouseId}`, { method: "DELETE" });
}

export function listVehicles(tenantId: string, includeArchived = false): Promise<FleetVehicle[]> {
  return request<FleetVehicle[]>(`/tenants/${tenantId}/vehicles?include_archived=${includeArchived}`);
}

export function createVehicle(tenantId: string, payload: FleetVehicleInput): Promise<FleetVehicle> {
  return request<FleetVehicle>(`/tenants/${tenantId}/vehicles`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateVehicle(
  tenantId: string,
  vehicleId: string,
  payload: Partial<FleetVehicleInput>,
): Promise<FleetVehicle> {
  return request<FleetVehicle>(`/tenants/${tenantId}/vehicles/${vehicleId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteVehicle(tenantId: string, vehicleId: string): Promise<void> {
  return request<void>(`/tenants/${tenantId}/vehicles/${vehicleId}`, { method: "DELETE" });
}

export function listOdooFleetVehicles(tenantId: string): Promise<OdooFleetVehicleList> {
  return request<OdooFleetVehicleList>(`/tenants/${tenantId}/vehicles/odoo-fleet-vehicles`);
}

export function linkVehicleToOdoo(
  tenantId: string,
  vehicleId: string,
  odooFleetVehicleId: number,
): Promise<FleetVehicle> {
  return request<FleetVehicle>(`/tenants/${tenantId}/vehicles/${vehicleId}/odoo-link`, {
    method: "PUT",
    body: JSON.stringify({ odoo_fleet_vehicle_id: odooFleetVehicleId }),
  });
}

export function unlinkVehicleFromOdoo(tenantId: string, vehicleId: string): Promise<FleetVehicle> {
  return request<FleetVehicle>(`/tenants/${tenantId}/vehicles/${vehicleId}/odoo-link`, {
    method: "DELETE",
  });
}

export function listDrivers(tenantId: string, includeArchived = false): Promise<Driver[]> {
  return request<Driver[]>(`/tenants/${tenantId}/drivers?include_archived=${includeArchived}`);
}

export function createDriver(tenantId: string, payload: DriverInput): Promise<Driver> {
  return request<Driver>(`/tenants/${tenantId}/drivers`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateDriver(
  tenantId: string,
  driverId: string,
  payload: Partial<DriverInput>,
): Promise<Driver> {
  return request<Driver>(`/tenants/${tenantId}/drivers/${driverId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteDriver(tenantId: string, driverId: string): Promise<void> {
  return request<void>(`/tenants/${tenantId}/drivers/${driverId}`, { method: "DELETE" });
}

export function listOdooEmployees(tenantId: string): Promise<OdooEmployeeList> {
  return request<OdooEmployeeList>(`/tenants/${tenantId}/drivers/odoo-employees`);
}

export function linkDriverToOdoo(
  tenantId: string,
  driverId: string,
  odooEmployeeId: number,
): Promise<Driver> {
  return request<Driver>(`/tenants/${tenantId}/drivers/${driverId}/odoo-link`, {
    method: "PUT",
    body: JSON.stringify({ odoo_employee_id: odooEmployeeId }),
  });
}

export function unlinkDriverFromOdoo(tenantId: string, driverId: string): Promise<Driver> {
  return request<Driver>(`/tenants/${tenantId}/drivers/${driverId}/odoo-link`, {
    method: "DELETE",
  });
}

export function getMe(): Promise<User> {
  return request<User>("/auth/me");
}

export function changeMyPassword(payload: SelfPasswordChangeInput): Promise<User> {
  return request<User>("/auth/password", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function listUsers(tenantId: string): Promise<User[]> {
  return request<User[]>(`/tenants/${tenantId}/users`);
}

export function createUser(tenantId: string, payload: UserCreateInput): Promise<User> {
  return request<User>(`/tenants/${tenantId}/users`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateUser(
  tenantId: string,
  userId: string,
  payload: UserUpdateInput,
): Promise<User> {
  return request<User>(`/tenants/${tenantId}/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteUser(tenantId: string, userId: string): Promise<void> {
  return request<void>(`/tenants/${tenantId}/users/${userId}`, { method: "DELETE" });
}

export function resetUserPassword(
  tenantId: string,
  userId: string,
  payload: AdminPasswordResetInput,
): Promise<User> {
  return request<User>(`/tenants/${tenantId}/users/${userId}/password`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
