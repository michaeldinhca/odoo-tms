export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OdooCredential {
  tenant_id: string;
  url: string;
  db: string;
  username: string;
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

export interface OperationType {
  id: string;
  tenant_id: string;
  odoo_operation_type_id: number;
  name: string;
  code: string;
  warehouse_id: number | null;
  is_synced: boolean;
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
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export type FleetVehicleType = "van" | "truck" | "motorbike" | "three_wheeler" | "other";
export type FleetVehicleStatus = "active" | "inactive" | "maintenance";
export type DriverStatus = "active" | "locked" | "inactive";
export type OdooLinkStatus = "unlinked" | "linked";

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
