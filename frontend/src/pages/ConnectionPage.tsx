import { type FormEvent, useEffect, useState } from "react";
import { getCredential, getTenantId, testCredential, upsertCredential } from "../api/client";
import type { OdooCredential, OdooCredentialTestResult } from "../api/types";

export default function ConnectionPage() {
  const tenantId = getTenantId();
  const [existing, setExisting] = useState<OdooCredential | null>(null);
  const [url, setUrl] = useState("");
  const [db, setDb] = useState("");
  const [username, setUsername] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<OdooCredentialTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setTestResult(null);
    setSaving(true);
    try {
      const credential = await upsertCredential(tenantId!, { url, db, username, api_key: apiKey });
      setExisting(credential);
      setApiKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save connection");
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to test connection");
    }
  }

  return (
    <div className="page page-narrow">
      <h1>Odoo connection</h1>
      {existing && (
        <p className="hint">
          Connected to <strong>{existing.url}</strong> (db: {existing.db}) as{" "}
          {existing.username}
        </p>
      )}
      <form onSubmit={handleSave}>
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
            {saving ? "Saving..." : "Save connection"}
          </button>
          {existing && (
            <button type="button" onClick={handleTest}>
              Test connection
            </button>
          )}
        </div>
      </form>
      {testResult && (
        <p className={testResult.success ? "success" : "error"}>{testResult.detail}</p>
      )}
    </div>
  );
}
