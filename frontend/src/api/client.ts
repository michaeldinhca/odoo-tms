import type {
  OdooCredential,
  OdooCredentialTestResult,
  OdooCredentialUpsert,
  PlanningRunResult,
  TokenResponse,
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

function decodeTenantId(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.tenant_id ?? null;
  } catch {
    return null;
  }
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

export function testCredential(tenantId: string): Promise<OdooCredentialTestResult> {
  return request<OdooCredentialTestResult>(`/tenants/${tenantId}/credentials/test`, {
    method: "POST",
  });
}

export function runPlanning(tenantId: string): Promise<PlanningRunResult> {
  return request<PlanningRunResult>("/planning/run", {
    method: "POST",
    body: JSON.stringify({ tenant_id: tenantId }),
  });
}
