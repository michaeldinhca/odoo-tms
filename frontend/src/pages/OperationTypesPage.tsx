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
import { Button, Card, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";
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

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  if (!instanceLoading && !isActive) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <h1 className="mb-2 text-2xl font-semibold text-text">Operation types</h1>
        <p className="text-sm text-text-muted">
          Connect and activate an Odoo instance first — see the{" "}
          <Link
            to="/connection"
            className="rounded-sm text-accent underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            Odoo connection
          </Link>{" "}
          page.
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
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Operation types</h1>
      <p className="mb-4 text-sm text-text-muted">
        Only pickings whose operation type is checked below get pulled by Run Planning. New
        operation types found in Odoo start unchecked — nothing syncs until you opt in.
      </p>
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <Button onClick={handlePreview} disabled={previewing || confirming}>
          {previewing ? "Checking Odoo..." : "Resync List"}
        </Button>
        <label className="flex items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
          Show archived
        </label>
      </div>
      {error && <p className="mb-4 text-sm text-status-full">{error}</p>}

      {preview && (
        <Card className="mb-4 flex flex-col gap-2">
          <p className="text-sm text-text">
            <strong className="font-medium">{preview.new.length}</strong> new,{" "}
            <strong className="font-medium">{preview.removed.length}</strong> no longer in Odoo,{" "}
            {preview.unchanged_count} unchanged.
          </p>
          {preview.new.length > 0 && (
            <p className="text-sm text-text-muted">New: {preview.new.map((i) => i.name).join(", ")}</p>
          )}
          {preview.removed.length > 0 && (
            <p className="text-sm text-text-muted">
              No longer in Odoo: {preview.removed.map((i) => i.name).join(", ")}
            </p>
          )}
          <div className="flex gap-2 pt-1">
            <Button size="sm" onClick={handleConfirmResync} disabled={confirming}>
              {confirming ? "Applying..." : "Confirm"}
            </Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => setPreview(null)}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {types.length === 0 ? (
        <p className="text-sm text-text-muted">
          No operation types yet — click "Resync List" to pull them from Odoo.
        </p>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <Th>Sync</Th>
              <Th>Name</Th>
              <Th>Code</Th>
              <Th>Warehouse (Odoo id)</Th>
              <Th>Last seen</Th>
              <Th>Actions</Th>
            </TableRow>
          </TableHead>
          <TableBody>
            {types.map((t) => (
              <TableRow key={t.id}>
                <Td>
                  <input
                    type="checkbox"
                    checked={t.is_synced}
                    onChange={() => handleToggle(t)}
                    aria-label={`Sync ${t.name}`}
                    className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  />
                </Td>
                <Td>{t.name}</Td>
                <Td>{t.code}</Td>
                <Td>{t.warehouse_id ?? "—"}</Td>
                <Td className="text-text-muted">{t.last_seen_at ?? "—"}</Td>
                <Td>
                  <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={() => handleArchiveToggle(t)}>
                      {t.active ? "Archive" : "Unarchive"}
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => handleDelete(t)}>
                      Delete
                    </Button>
                  </div>
                </Td>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
