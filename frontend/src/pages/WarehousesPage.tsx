import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  deleteOperationType,
  deleteWarehouse,
  getTenantId,
  listOperationTypes,
  listWarehouses,
  previewOperationTypesRefresh,
  previewWarehousesRefresh,
  refreshOperationTypes,
  refreshWarehouses,
  setOperationTypeActive,
  setOperationTypeSync,
  setWarehouseActive,
  setWarehouseCoordinates,
  setWarehouseSync,
} from "../api/client";
import type {
  OperationType,
  OperationTypeRefreshPreview,
  Warehouse,
  WarehouseRefreshPreview,
} from "../api/types";
import { Button, Card, Input, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";
import { useCurrentUser } from "../context/CurrentUserContext";
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
  const { hasPermission } = useCurrentUser();
  const canManageWarehouses = hasPermission("can_manage_warehouses");
  const canManageOperationTypes = hasPermission("can_manage_operation_types");

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [preview, setPreview] = useState<WarehouseRefreshPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const [editingCoordsId, setEditingCoordsId] = useState<string | null>(null);
  const [coordsForm, setCoordsForm] = useState({ lat: "", lng: "" });

  const [operationTypes, setOperationTypes] = useState<OperationType[]>([]);
  const [showArchivedOperationTypes, setShowArchivedOperationTypes] = useState(false);
  const [operationTypeError, setOperationTypeError] = useState<string | null>(null);
  const [operationTypePreview, setOperationTypePreview] = useState<OperationTypeRefreshPreview | null>(
    null,
  );
  const [previewingOperationTypes, setPreviewingOperationTypes] = useState(false);
  const [confirmingOperationTypes, setConfirmingOperationTypes] = useState(false);

  function loadWarehouses() {
    if (!tenantId) return;
    listWarehouses(tenantId, showArchived)
      .then(setWarehouses)
      .catch(() => {
        // no warehouses synced yet — leave the table empty
      });
  }

  useEffect(loadWarehouses, [tenantId, showArchived]);

  function loadOperationTypes() {
    if (!tenantId) return;
    listOperationTypes(tenantId, showArchivedOperationTypes)
      .then(setOperationTypes)
      .catch(() => {
        // no operation types synced yet — leave the table empty
      });
  }

  useEffect(loadOperationTypes, [tenantId, showArchivedOperationTypes]);

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  if (!instanceLoading && !isActive) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <h1 className="mb-2 text-2xl font-semibold text-text">Warehouses &amp; Operation Types</h1>
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
      // Un-syncing a warehouse changes which operation types are in scope
      // (see DECISIONS.md) — refresh that list too so it stays consistent
      // without a manual reload.
      loadOperationTypes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update sync setting");
    }
  }

  async function handleArchiveToggle(warehouse: Warehouse) {
    setError(null);
    try {
      await setWarehouseActive(tenantId!, warehouse.id, !warehouse.active);
      loadWarehouses();
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

  function handleStartEditCoords(warehouse: Warehouse) {
    setEditingCoordsId(warehouse.id);
    setCoordsForm({
      lat: warehouse.lat != null ? String(warehouse.lat) : "",
      lng: warehouse.lng != null ? String(warehouse.lng) : "",
    });
  }

  async function handleSaveCoords(warehouse: Warehouse) {
    setError(null);
    try {
      const updated = await setWarehouseCoordinates(tenantId!, warehouse.id, {
        lat: coordsForm.lat ? Number(coordsForm.lat) : null,
        lng: coordsForm.lng ? Number(coordsForm.lng) : null,
      });
      setWarehouses((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
      setEditingCoordsId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save coordinates");
    }
  }

  async function handlePreviewOperationTypes() {
    setOperationTypeError(null);
    setPreviewingOperationTypes(true);
    try {
      setOperationTypePreview(await previewOperationTypesRefresh(tenantId!));
    } catch (err) {
      setOperationTypeError(err instanceof Error ? err.message : "Failed to preview resync");
    } finally {
      setPreviewingOperationTypes(false);
    }
  }

  async function handleConfirmOperationTypesResync() {
    setOperationTypeError(null);
    setConfirmingOperationTypes(true);
    try {
      setOperationTypes(await refreshOperationTypes(tenantId!));
      setOperationTypePreview(null);
    } catch (err) {
      setOperationTypeError(err instanceof Error ? err.message : "Failed to refresh operation types");
    } finally {
      setConfirmingOperationTypes(false);
    }
  }

  async function handleToggleOperationType(operationType: OperationType) {
    setOperationTypeError(null);
    try {
      const updated = await setOperationTypeSync(
        tenantId!,
        operationType.id,
        !operationType.is_synced,
      );
      setOperationTypes((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      setOperationTypeError(err instanceof Error ? err.message : "Failed to update sync setting");
    }
  }

  async function handleArchiveToggleOperationType(operationType: OperationType) {
    setOperationTypeError(null);
    try {
      await setOperationTypeActive(tenantId!, operationType.id, !operationType.active);
      loadOperationTypes();
    } catch (err) {
      setOperationTypeError(err instanceof Error ? err.message : "Failed to update archive state");
    }
  }

  async function handleDeleteOperationType(operationType: OperationType) {
    setOperationTypeError(null);
    try {
      await deleteOperationType(tenantId!, operationType.id);
      setOperationTypes((prev) => prev.filter((t) => t.id !== operationType.id));
    } catch (err) {
      setOperationTypeError(err instanceof Error ? err.message : "Failed to delete operation type");
    }
  }

  const syncedWarehouseCount = warehouses.filter((w) => w.is_synced).length;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Warehouses &amp; Operation Types</h1>
      <p className="mb-6 text-sm text-text-muted">
        Sync a warehouse first — only operation types belonging to a synced warehouse can be
        managed below.
      </p>

      {canManageWarehouses && (
        <Card heading="Warehouses" className="mb-6">
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
                <p className="text-sm text-text-muted">
                  New: {preview.new.map((i) => i.name).join(", ")}
                </p>
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
                  <Th>Coordinates</Th>
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
                    <Td>
                      {editingCoordsId === w.id ? (
                        <div className="flex items-center gap-1">
                          <Input
                            type="number"
                            step="any"
                            placeholder="lat"
                            value={coordsForm.lat}
                            onChange={(e) => setCoordsForm({ ...coordsForm, lat: e.target.value })}
                            className="w-24 px-2 py-1"
                          />
                          <Input
                            type="number"
                            step="any"
                            placeholder="lng"
                            value={coordsForm.lng}
                            onChange={(e) => setCoordsForm({ ...coordsForm, lng: e.target.value })}
                            className="w-24 px-2 py-1"
                          />
                          <Button size="sm" onClick={() => handleSaveCoords(w)}>
                            Save
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => setEditingCoordsId(null)}>
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleStartEditCoords(w)}
                          className="rounded-sm text-left text-text-muted hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        >
                          {w.lat != null && w.lng != null ? `${w.lat}, ${w.lng}` : "Set coordinates"}
                        </button>
                      )}
                    </Td>
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
        </Card>
      )}

      {canManageOperationTypes && (
        <Card heading="Operation Types">
          <p className="mb-4 text-sm text-text-muted">
            Only pickings whose operation type is checked below get pulled by Run Planning.
            Operation types are scoped to synced warehouses —{" "}
            {syncedWarehouseCount === 0
              ? "sync a warehouse above first."
              : "new ones found in Odoo start unchecked, nothing syncs until you opt in."}
          </p>
          <div className="mb-4 flex flex-wrap items-center gap-4">
            <Button
              onClick={handlePreviewOperationTypes}
              disabled={previewingOperationTypes || confirmingOperationTypes || syncedWarehouseCount === 0}
            >
              {previewingOperationTypes ? "Checking Odoo..." : "Resync List"}
            </Button>
            <label className="flex items-center gap-2 text-sm text-text">
              <input
                type="checkbox"
                checked={showArchivedOperationTypes}
                onChange={(e) => setShowArchivedOperationTypes(e.target.checked)}
                className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              />
              Show archived
            </label>
          </div>
          {operationTypeError && <p className="mb-4 text-sm text-status-full">{operationTypeError}</p>}

          {operationTypePreview && (
            <Card className="mb-4 flex flex-col gap-2">
              <p className="text-sm text-text">
                <strong className="font-medium">{operationTypePreview.new.length}</strong> new,{" "}
                <strong className="font-medium">{operationTypePreview.removed.length}</strong> no
                longer in Odoo, {operationTypePreview.unchanged_count} unchanged.
              </p>
              {operationTypePreview.new.length > 0 && (
                <p className="text-sm text-text-muted">
                  New: {operationTypePreview.new.map((i) => i.name).join(", ")}
                </p>
              )}
              {operationTypePreview.removed.length > 0 && (
                <p className="text-sm text-text-muted">
                  No longer in Odoo: {operationTypePreview.removed.map((i) => i.name).join(", ")}
                </p>
              )}
              <div className="flex gap-2 pt-1">
                <Button size="sm" onClick={handleConfirmOperationTypesResync} disabled={confirmingOperationTypes}>
                  {confirmingOperationTypes ? "Applying..." : "Confirm"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => setOperationTypePreview(null)}
                >
                  Cancel
                </Button>
              </div>
            </Card>
          )}

          {operationTypes.length === 0 ? (
            <p className="text-sm text-text-muted">
              {syncedWarehouseCount === 0
                ? "No synced warehouses yet."
                : 'No operation types yet — click "Resync List" to pull them from Odoo.'}
            </p>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <Th>Sync</Th>
                  <Th>Name</Th>
                  <Th>Code</Th>
                  <Th>Warehouse</Th>
                  <Th>Last seen</Th>
                  <Th>Actions</Th>
                </TableRow>
              </TableHead>
              <TableBody>
                {operationTypes.map((t) => (
                  <TableRow key={t.id}>
                    <Td>
                      <input
                        type="checkbox"
                        checked={t.is_synced}
                        onChange={() => handleToggleOperationType(t)}
                        aria-label={`Sync ${t.name}`}
                        className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                      />
                    </Td>
                    <Td>{t.name}</Td>
                    <Td>{t.code}</Td>
                    <Td>{t.warehouse_name ?? "—"}</Td>
                    <Td className="text-text-muted">{t.last_seen_at ?? "—"}</Td>
                    <Td>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleArchiveToggleOperationType(t)}
                        >
                          {t.active ? "Archive" : "Unarchive"}
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => handleDeleteOperationType(t)}>
                          Delete
                        </Button>
                      </div>
                    </Td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      )}
    </div>
  );
}
