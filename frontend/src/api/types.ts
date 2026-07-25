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
  street1: string;
  street2: string;
  city: string;
  country: string;
  zip: string;
}

export interface RouteStop {
  stop_order: number;
  picking_id: number;
  customer_name: string;
  items_summary: string;
  address: Address;
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
