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
