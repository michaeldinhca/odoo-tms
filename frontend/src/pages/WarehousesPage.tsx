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
import { Button, Card, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";
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

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  if (!instanceLoading && !isActive) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <h1 className="mb-2 text-2xl font-semibold text-text">Warehouses</h1>
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
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Warehouses</h1>
      <p className="mb-4 text-sm text-text-muted">
        Warehouses resolved onto a picking's route come from the ones checked below.
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

      {warehouses.length === 0 ? (
        <p className="text-sm text-text-muted">
          No warehouses yet — click "Resync List" to pull them from Odoo.
        </p>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <Th>Sync</Th>
              <Th>Name</Th>
              <Th>Code</Th>
              <Th>Address</Th>
              <Th>Last seen</Th>
              <Th>Actions</Th>
            </TableRow>
          </TableHead>
          <TableBody>
            {warehouses.map((w) => (
              <TableRow key={w.id}>
                <Td>
                  <input
                    type="checkbox"
                    checked={w.is_synced}
                    onChange={() => handleToggle(w)}
                    aria-label={`Sync ${w.name}`}
                    className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  />
                </Td>
                <Td>{w.name}</Td>
                <Td>{w.code}</Td>
                <Td>{formatWarehouseAddress(w)}</Td>
                <Td className="text-text-muted">{w.last_seen_at ?? "—"}</Td>
                <Td>
                  <div className="flex gap-2">
                    <Button size="sm" variant="secondary" onClick={() => handleArchiveToggle(w)}>
                      {w.active ? "Archive" : "Unarchive"}
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => handleDelete(w)}>
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
