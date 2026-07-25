import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  deleteWarehouse,
  getTenantId,
  listWarehouses,
  previewWarehousesRefresh,
  refreshWarehouses,
  setWarehouseActive,
  setWarehouseSync,
} from "../api/client";
import type { Warehouse, WarehouseRefreshPreview } from "../api/types";
import { useOdooInstance } from "../context/OdooInstanceContext";

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
  const { isActive, loading: instanceLoading } = useOdooInstance();
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [preview, setPreview] = useState<WarehouseRefreshPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  function load() {
    if (!tenantId) return;
    listWarehouses(tenantId, showArchived)
      .then(setWarehouses)
      .catch(() => {
        // no warehouses synced yet — leave the table empty
      });
  }

  useEffect(load, [tenantId, showArchived]);

  if (!tenantId) return <p className="page">Not logged in.</p>;

  if (!instanceLoading && !isActive) {
    return (
      <div className="page">
        <h1>Warehouses</h1>
        <p className="hint">
          Connect and activate an Odoo instance first — see the{" "}
          <Link to="/connection">Odoo connection</Link> page.
        </p>
      </div>
    );
  }

  async function handlePreview() {
    setError(null);
    setPreviewing(true);
    try {
      setPreview(await previewWarehousesRefresh(tenantId!));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to preview resync");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleConfirmResync() {
    setError(null);
    setConfirming(true);
    try {
      setWarehouses(await refreshWarehouses(tenantId!));
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh warehouses");
    } finally {
      setConfirming(false);
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

  async function handleArchiveToggle(warehouse: Warehouse) {
    setError(null);
    try {
      await setWarehouseActive(tenantId!, warehouse.id, !warehouse.active);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update archive state");
    }
  }

  async function handleDelete(warehouse: Warehouse) {
    setError(null);
    try {
      await deleteWarehouse(tenantId!, warehouse.id);
      setWarehouses((prev) => prev.filter((w) => w.id !== warehouse.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete warehouse");
    }
  }

  return (
    <div className="page">
      <h1>Warehouses</h1>
      <p className="hint">
        Warehouses resolved onto a picking's route come from the ones checked below.
      </p>
      <div className="actions">
        <button onClick={handlePreview} disabled={previewing || confirming}>
          {previewing ? "Checking Odoo..." : "Resync List"}
        </button>
        <label>
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
          />{" "}
          Show archived
        </label>
      </div>
      {error && <p className="error">{error}</p>}

      {preview && (
        <div className="preview-panel">
          <p>
            <strong>{preview.new.length}</strong> new,{" "}
            <strong>{preview.removed.length}</strong> no longer in Odoo,{" "}
            {preview.unchanged_count} unchanged.
          </p>
          {preview.new.length > 0 && (
            <p className="hint">New: {preview.new.map((i) => i.name).join(", ")}</p>
          )}
          {preview.removed.length > 0 && (
            <p className="hint">No longer in Odoo: {preview.removed.map((i) => i.name).join(", ")}</p>
          )}
          <div className="actions">
            <button onClick={handleConfirmResync} disabled={confirming}>
              {confirming ? "Applying..." : "Confirm"}
            </button>
            <button type="button" onClick={() => setPreview(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

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
              <th>Actions</th>
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
                <td>
                  <button type="button" onClick={() => handleArchiveToggle(w)}>
                    {w.active ? "Archive" : "Unarchive"}
                  </button>
                  <button type="button" onClick={() => handleDelete(w)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
