export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type OdooConnectionState = "draft" | "active" | "error";

export interface OdooCredential {
  tenant_id: string;
  url: string;
  db: string;
  username: string;
  state: OdooConnectionState;
  activated_at: string | null;
  last_synced_operation_types_at: string | null;
  last_synced_warehouses_at: string | null;
  company_id: number | null;
  company_name: string | null;
  server_version: string | null;
  server_version_major: number | null;
  server_serie: string | null;
  protocol_version: number | null;
  version_checked_at: string | null;
  version_change_detected: boolean;
  created_at: string;
}

export interface OdooCredentialUpsert {
  url: string;
  db: string;
  username: string;
  api_key: string;
}

export interface OdooCredentialTestResult {
  success: boolean;
  detail: string;
  server_version: string | null;
  server_version_major: number | null;
  version_change_detected: boolean;
}

export interface OdooCompany {
  id: number;
  name: string;
}

export interface Address {
  street: string;
  street2: string;
  city: string;
  state_id: number | null;
  state_name: string;
  country_id: number | null;
  country_name: string;
  zip: string;
}

export interface RouteStop {
  stop_order: number;
  picking_id: number;
  customer_name: string;
  items_summary: string;
  address: Address;
  state: string;
  scheduled_date: string | null;
  origin: string;
  warehouse_name: string;
  eta: string | null;
}

export interface VehicleRoute {
  vehicle_id: number;
  sequence: RouteStop[];
  estimated_distance_km: number;
  estimated_duration_min: number;
}

export interface PlanningRunResult {
  run_id: string;
  tenant_id: string;
  status: string;
  routes: VehicleRoute[];
  unassigned_picking_ids: number[];
  created_at: string;
  completed_at: string | null;
}

/** Scoped to synced warehouses server-side — the list this type describes
 * never includes a row for a warehouse that isn't currently synced (see
 * DECISIONS.md). `warehouse_name` is resolved at read time, not stored. */
export interface OperationType {
  id: string;
  tenant_id: string;
  odoo_operation_type_id: number;
  name: string;
  code: string;
  warehouse_id: number | null;
  warehouse_name: string | null;
  is_synced: boolean;
  active: boolean;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Warehouse {
  id: string;
  tenant_id: string;
  odoo_warehouse_id: number;
  name: string;
  code: string;
  street: string;
  street2: string;
  city: string;
  state_id: number | null;
  state_name: string;
  country_id: number | null;
  country_name: string;
  zip: string;
  is_synced: boolean;
  active: boolean;
  /** Admin-entered, not synced from Odoo — see SPEC.md. Null until set via
   * setWarehouseCoordinates; needed for the distance shown on that
   * warehouse's destination route set. */
  lat: number | null;
  lng: number | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WarehouseCoordinatesInput {
  lat: number | null;
  lng: number | null;
}

/** `lat`/`lng` are null for a destination auto-created from a
 * stock.picking address (see DECISIONS.md) that hasn't had coordinates
 * filled in yet — manual creation (DestinationLocationInput below) still
 * always requires them. */
export interface DestinationLocation {
  id: string;
  tenant_id: string;
  name: string;
  street: string;
  street2: string;
  city: string;
  state: string;
  country: string;
  zip: string;
  lat: number | null;
  lng: number | null;
  created_at: string;
  updated_at: string;
}

export interface DestinationLocationInput {
  name: string;
  street?: string;
  street2?: string;
  city?: string;
  state?: string;
  country?: string;
  zip?: string;
  lat: number;
  lng: number;
}

export type DestinationLocationUpdateInput = Partial<DestinationLocationInput>;

export interface PickingAddressOption {
  customer_name: string;
  street: string;
  street2: string;
  city: string;
  state_name: string;
  country_name: string;
  zip: string;
}

/** One destination's position within a WarehouseRoute — named distinctly
 * from the existing `RouteStop` above (that one is a planning-run FILO
 * result stop, an unrelated concept that happens to share the word
 * "route"). Distance is computed at read time from both sides' current
 * lat/lng (null if the warehouse has no coordinates set yet). */
export interface WarehouseRouteStop {
  id: string;
  destination: DestinationLocation;
  stop_order: number;
  distance_km: number | null;
  created_at: string;
}

/** A named, colored delivery route belonging to one warehouse — an
 * ordered sequence of WarehouseRouteStops. Replaces the earlier flat,
 * unordered "warehouse route set" concept. */
export interface WarehouseRoute {
  id: string;
  tenant_id: string;
  warehouse_id: string;
  name: string;
  color: string;
  stops: WarehouseRouteStop[];
  created_at: string;
  updated_at: string;
}

export interface WarehouseRouteInput {
  name: string;
  color?: string | null;
}

/** `skipped_destination_ids` are ones already in the route — bulk-add
 * silently skips duplicates rather than failing the whole batch, but
 * still reports what was skipped. */
export interface BulkAddRouteStopsResult {
  stops: WarehouseRouteStop[];
  skipped_destination_ids: string[];
}

export interface OperationTypeDiffItem {
  odoo_operation_type_id: number;
  name: string;
  code: string;
}

export interface OperationTypeRefreshPreview {
  new: OperationTypeDiffItem[];
  removed: OperationTypeDiffItem[];
  unchanged_count: number;
}

export interface WarehouseDiffItem {
  odoo_warehouse_id: number;
  name: string;
  code: string;
}

export interface WarehouseRefreshPreview {
  new: WarehouseDiffItem[];
  removed: WarehouseDiffItem[];
  unchanged_count: number;
}

export type FleetVehicleType = "van" | "truck" | "motorbike" | "three_wheeler" | "other";
export type FleetVehicleStatus = "active" | "inactive" | "maintenance";
export type DriverStatus = "active" | "locked" | "inactive";
export type OdooLinkStatus = "unlinked" | "linked" | "stale";

export interface FleetVehicle {
  id: string;
  tenant_id: string;
  name: string;
  license_plate: string | null;
  vehicle_type: FleetVehicleType;
  payload_capacity_kg: number | null;
  volume_capacity_m3: number | null;
  fuel_consumption_per_100km: number | null;
  home_warehouse_id: string | null;
  status: FleetVehicleStatus;
  odoo_fleet_vehicle_id: number | null;
  odoo_link_status: OdooLinkStatus;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FleetVehicleInput {
  name: string;
  license_plate?: string | null;
  vehicle_type?: FleetVehicleType;
  payload_capacity_kg?: number | null;
  volume_capacity_m3?: number | null;
  fuel_consumption_per_100km?: number | null;
  home_warehouse_id?: string | null;
  status?: FleetVehicleStatus;
  active?: boolean;
}

export interface Driver {
  id: string;
  tenant_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  license_number: string | null;
  id_passport_number: string | null;
  status: DriverStatus;
  locked_until: string | null;
  assigned_vehicle_id: string | null;
  odoo_employee_id: number | null;
  odoo_link_status: OdooLinkStatus;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DriverInput {
  name: string;
  phone?: string | null;
  email?: string | null;
  license_number?: string | null;
  id_passport_number?: string | null;
  status?: DriverStatus;
  locked_until?: string | null;
  assigned_vehicle_id?: string | null;
  active?: boolean;
}

export interface OdooFleetVehicleOption {
  id: number;
  name: string;
  license_plate: string;
}

export interface OdooFleetVehicleList {
  available: boolean;
  vehicles: OdooFleetVehicleOption[];
}

export interface OdooEmployeeOption {
  id: number;
  name: string;
  work_phone: string;
  mobile_phone: string;
}

export interface OdooEmployeeList {
  available: boolean;
  employees: OdooEmployeeOption[];
}

export type UserRole = "admin" | "user";

/** `role` only gates the Users page itself (see `CurrentUserContext`'s
 * `isAdmin`); every other feature is gated by its own `can_*` boolean,
 * for both roles alike — see design.md "Role vs. boolean permissions". */
export interface User {
  id: string;
  tenant_id: string;
  email: string;
  role: UserRole;
  can_manage_connection: boolean;
  can_manage_warehouses: boolean;
  can_manage_operation_types: boolean;
  can_manage_fleet: boolean;
  can_run_planning: boolean;
  can_use_load_planning: boolean;
  created_at: string;
}

export interface UserCreateInput {
  email: string;
  password: string;
  role: UserRole;
  can_manage_connection: boolean;
  can_manage_warehouses: boolean;
  can_manage_operation_types: boolean;
  can_manage_fleet: boolean;
  can_run_planning: boolean;
  can_use_load_planning: boolean;
}

export type UserUpdateInput = Partial<Omit<UserCreateInput, "password">>;

export interface AdminPasswordResetInput {
  new_password: string;
}

export interface SelfPasswordChangeInput {
  current_password: string;
  new_password: string;
}
