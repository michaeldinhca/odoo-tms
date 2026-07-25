import { type FormEvent, useEffect, useState } from "react";
import {
  getCredential,
  getTenantId,
  listCompanies,
  reauthenticateCredential,
  selectCompany,
  testCredential,
  upsertCredential,
} from "../api/client";
import type { OdooCompany, OdooCredential, OdooCredentialTestResult } from "../api/types";
import { useOdooInstance } from "../context/OdooInstanceContext";

export default function ConnectionPage() {
  const tenantId = getTenantId();
  const { refetch: refetchInstance } = useOdooInstance();
  const [existing, setExisting] = useState<OdooCredential | null>(null);
  const [url, setUrl] = useState("");
  const [db, setDb] = useState("");
  const [username, setUsername] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<OdooCredentialTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reauthenticating, setReauthenticating] = useState(false);

  const [companies, setCompanies] = useState<OdooCompany[] | null>(null);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [savingCompany, setSavingCompany] = useState(false);
  const [companyError, setCompanyError] = useState<string | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    getCredential(tenantId)
      .then((credential) => {
        setExisting(credential);
        setUrl(credential.url);
        setDb(credential.db);
        setUsername(credential.username);
      })
      .catch(() => {
        // no connection configured yet — leave the form blank
      });
  }, [tenantId]);

  if (!tenantId) return <p className="page">Not logged in.</p>;

  const isActive = existing?.state === "active";

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setTestResult(null);
    setSaving(true);
    try {
      const credential = await upsertCredential(tenantId!, { url, db, username, api_key: apiKey });
      setExisting(credential);
      setApiKey("");
      refetchInstance();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save connection");
    } finally {
      setSaving(false);
    }
  }

  async function handleReauthenticate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const credential = await reauthenticateCredential(tenantId!, { url, db, username, api_key: apiKey });
      setExisting(credential);
      setApiKey("");
      setReauthenticating(false);
      refetchInstance();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to re-authenticate connection");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setError(null);
    setTestResult(null);
    try {
      const result = await testCredential(tenantId!);
      setTestResult(result);
      if (result.success) {
        // test_credential persists the freshly-detected version server-side;
        // re-fetch so the displayed version/warning reflect this check.
        setExisting(await getCredential(tenantId!));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to test connection");
    }
  }

  async function handleLoadCompanies() {
    setCompanyError(null);
    setLoadingCompanies(true);
    try {
      const list = await listCompanies(tenantId!);
      setCompanies(list);
      setSelectedCompanyId(existing?.company_id != null ? String(existing.company_id) : "");
    } catch (err) {
      setCompanyError(err instanceof Error ? err.message : "Failed to load companies");
    } finally {
      setLoadingCompanies(false);
    }
  }

  async function handleSaveCompany() {
    setCompanyError(null);
    setSavingCompany(true);
    try {
      const companyId = selectedCompanyId === "" ? null : Number(selectedCompanyId);
      const companyName =
        companyId === null ? null : (companies?.find((c) => c.id === companyId)?.name ?? null);
      const updated = await selectCompany(tenantId!, companyId, companyName);
      setExisting(updated);
      refetchInstance();
    } catch (err) {
      setCompanyError(err instanceof Error ? err.message : "Failed to save company selection");
    } finally {
      setSavingCompany(false);
    }
  }

  return (
    <div className="page page-narrow">
      <h1>Odoo connection</h1>

      {existing && (
        <p className={isActive ? "success" : "hint"}>
          {isActive ? "Active — " : "Draft (not yet activated) — "}
          <strong>{existing.url}</strong> (db: {existing.db}) as {existing.username}
        </p>
      )}
      {existing?.server_version && (
        <p className="hint">
          Connected — Odoo {existing.server_version}
          {existing.version_change_detected && (
            <span className="error">
              {" "}
              ⚠ Odoo's major version changed since the last check — field mappings may need
              re-verifying (see SPEC.md's Odoo field mappings).
            </span>
          )}
        </p>
      )}

      {isActive && !reauthenticating ? (
        <div className="actions">
          <button type="button" onClick={handleTest}>
            Test connection
          </button>
          <button type="button" onClick={() => setReauthenticating(true)}>
            Re-authenticate connection
          </button>
        </div>
      ) : (
        <form onSubmit={isActive ? handleReauthenticate : handleSave}>
          {isActive && (
            <p className="hint">
              Re-authenticating updates the URL, database, username, or API key on this active
              connection — it never resets your company selection or Operation Types/Warehouses.
            </p>
          )}
          <label>
            Odoo URL
            <input
              type="url"
              placeholder="https://customer.odoo.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
          </label>
          <label>
            Database
            <input value={db} onChange={(e) => setDb(e.target.value)} required />
          </label>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            API key
            <input
              type="password"
              placeholder={existing ? "Re-enter to update" : ""}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
            />
          </label>
          {existing && (
            <p className="hint">
              The API key is never shown once saved — re-enter it here any time you want to
              update the connection.
            </p>
          )}
          {error && <p className="error">{error}</p>}
          <div className="actions">
            <button type="submit" disabled={saving}>
              {saving ? "Saving..." : isActive ? "Confirm re-authentication" : "Save connection"}
            </button>
            {!isActive && existing && (
              <button type="button" onClick={handleTest}>
                Test connection
              </button>
            )}
            {isActive && (
              <button type="button" onClick={() => setReauthenticating(false)}>
                Cancel
              </button>
            )}
          </div>
        </form>
      )}
      {testResult && (
        <p className={testResult.success ? "success" : "error"}>{testResult.detail}</p>
      )}

      {existing && (
        <div className="company-section">
          <h2>Company</h2>
          <p className="hint">
            {isActive
              ? "An Odoo instance can have several companies. Planning runs are scoped to the company selected here."
              : "Selecting a company (or explicitly choosing \"All companies\") activates this connection and unlocks Operation Types, Warehouses, and Odoo fleet/employee linking."}
          </p>
          <p>
            Currently scoped to: <strong>{existing.company_name ?? "All companies"}</strong>
          </p>
          <div className="actions">
            <button type="button" onClick={handleLoadCompanies} disabled={loadingCompanies}>
              {loadingCompanies ? "Loading..." : "Load companies from Odoo"}
            </button>
          </div>
          {companies && (
            <div className="actions company-select-row">
              <select
                value={selectedCompanyId}
                onChange={(e) => setSelectedCompanyId(e.target.value)}
              >
                <option value="">All companies</option>
                {companies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              <button type="button" onClick={handleSaveCompany} disabled={savingCompany}>
                {savingCompany ? "Saving..." : isActive ? "Save company" : "Activate connection"}
              </button>
            </div>
          )}
          {companyError && <p className="error">{companyError}</p>}
        </div>
      )}
    </div>
  );
}
