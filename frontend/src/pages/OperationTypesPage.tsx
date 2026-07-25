import { useEffect, useState } from "react";
import {
  getTenantId,
  listOperationTypes,
  refreshOperationTypes,
  setOperationTypeSync,
} from "../api/client";
import type { OperationType } from "../api/types";

export default function OperationTypesPage() {
  const tenantId = getTenantId();
  const [types, setTypes] = useState<OperationType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    listOperationTypes(tenantId).then(setTypes).catch(() => {
      // no operation types synced yet — leave the table empty
    });
  }, [tenantId]);

  if (!tenantId) return <p className="page">Not logged in.</p>;

  async function handleResync() {
    setError(null);
    setLoading(true);
    try {
      setTypes(await refreshOperationTypes(tenantId!));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh operation types");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(operationType: OperationType) {
    setError(null);
    try {
      const updated = await setOperationTypeSync(
        tenantId!,
        operationType.id,
        !operationType.is_synced,
      );
      setTypes((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update sync setting");
    }
  }

  return (
    <div className="page">
      <h1>Operation types</h1>
      <p className="hint">
        Only pickings whose operation type is checked below get pulled by Run Planning. New
        operation types found in Odoo start unchecked — nothing syncs until you opt in.
      </p>
      <div className="actions">
        <button onClick={handleResync} disabled={loading}>
          {loading ? "Resyncing..." : "Resync List"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      {types.length === 0 ? (
        <p className="hint">No operation types yet — click "Resync List" to pull them from Odoo.</p>
      ) : (
        <table className="route-table">
          <thead>
            <tr>
              <th>Sync</th>
              <th>Name</th>
              <th>Code</th>
              <th>Warehouse (Odoo id)</th>
              <th>Last seen</th>
            </tr>
          </thead>
          <tbody>
            {types.map((t) => (
              <tr key={t.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={t.is_synced}
                    onChange={() => handleToggle(t)}
                    aria-label={`Sync ${t.name}`}
                  />
                </td>
                <td>{t.name}</td>
                <td>{t.code}</td>
                <td>{t.warehouse_id ?? "—"}</td>
                <td>{t.last_seen_at ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
