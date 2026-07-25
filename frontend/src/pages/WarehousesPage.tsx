import { useEffect, useState } from "react";
import { getTenantId, listWarehouses, refreshWarehouses, setWarehouseSync } from "../api/client";
import type { Warehouse } from "../api/types";

function formatWarehouseAddress(w: Warehouse): string {
  const parts = [
    [w.street, w.street2].filter(Boolean).join(", "),
    w.city,
    w.zip,
    w.country_name,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "—";
}

export default function WarehousesPage() {
  const tenantId = getTenantId();
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    listWarehouses(tenantId).then(setWarehouses).catch(() => {
      // no warehouses synced yet — leave the table empty
    });
  }, [tenantId]);

  if (!tenantId) return <p className="page">Not logged in.</p>;

  async function handleResync() {
    setError(null);
    setLoading(true);
    try {
      setWarehouses(await refreshWarehouses(tenantId!));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh warehouses");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(warehouse: Warehouse) {
    setError(null);
    try {
      const updated = await setWarehouseSync(tenantId!, warehouse.id, !warehouse.is_synced);
      setWarehouses((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update sync setting");
    }
  }

  return (
    <div className="page">
      <h1>Warehouses</h1>
      <p className="hint">
        Warehouses resolved onto a picking's route come from the ones checked below.
      </p>
      <div className="actions">
        <button onClick={handleResync} disabled={loading}>
          {loading ? "Resyncing..." : "Resync List"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}

      {warehouses.length === 0 ? (
        <p className="hint">No warehouses yet — click "Resync List" to pull them from Odoo.</p>
      ) : (
        <table className="route-table">
          <thead>
            <tr>
              <th>Sync</th>
              <th>Name</th>
              <th>Code</th>
              <th>Address</th>
              <th>Last seen</th>
            </tr>
          </thead>
          <tbody>
            {warehouses.map((w) => (
              <tr key={w.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={w.is_synced}
                    onChange={() => handleToggle(w)}
                    aria-label={`Sync ${w.name}`}
                  />
                </td>
                <td>{w.name}</td>
                <td>{w.code}</td>
                <td>{formatWarehouseAddress(w)}</td>
                <td>{w.last_seen_at ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
