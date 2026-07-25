export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OdooCredential {
  tenant_id: string;
  url: string;
  db: string;
  username: string;
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

export interface RouteStop {
  stop_order: number;
  picking_id: number;
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
