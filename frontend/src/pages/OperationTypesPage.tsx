import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  deleteOperationType,
  getTenantId,
  listOperationTypes,
  previewOperationTypesRefresh,
  refreshOperationTypes,
  setOperationTypeActive,
  setOperationTypeSync,
} from "../api/client";
import type { OperationType, OperationTypeRefreshPreview } from "../api/types";
import { useOdooInstance } from "../context/OdooInstanceContext";

export default function OperationTypesPage() {
  const tenantId = getTenantId();
  const { isActive, loading: instanceLoading } = useOdooInstance();
  const [types, setTypes] = useState<OperationType[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [preview, setPreview] = useState<OperationTypeRefreshPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  function load() {
    if (!tenantId) return;
    listOperationTypes(tenantId, showArchived)
      .then(setTypes)
      .catch(() => {
        // no operation types synced yet — leave the table empty
      });
  }

  useEffect(load, [tenantId, showArchived]);

  if (!tenantId) return <p className="page">Not logged in.</p>;

  if (!instanceLoading && !isActive) {
    return (
      <div className="page">
        <h1>Operation types</h1>
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
      setPreview(await previewOperationTypesRefresh(tenantId!));
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
      setTypes(await refreshOperationTypes(tenantId!));
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh operation types");
    } finally {
      setConfirming(false);
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

  async function handleArchiveToggle(operationType: OperationType) {
    setError(null);
    try {
      await setOperationTypeActive(tenantId!, operationType.id, !operationType.active);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update archive state");
    }
  }

  async function handleDelete(operationType: OperationType) {
    setError(null);
    try {
      await deleteOperationType(tenantId!, operationType.id);
      setTypes((prev) => prev.filter((t) => t.id !== operationType.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete operation type");
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
              <th>Actions</th>
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
                <td>
                  <button type="button" onClick={() => handleArchiveToggle(t)}>
                    {t.active ? "Archive" : "Unarchive"}
                  </button>
                  <button type="button" onClick={() => handleDelete(t)}>
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
