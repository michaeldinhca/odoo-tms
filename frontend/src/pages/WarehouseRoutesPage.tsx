import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  bulkAddRouteStops,
  createWarehouseRoute,
  deleteWarehouseRoute,
  getTenantId,
  listDestinationLocations,
  listWarehouseRoutes,
  listWarehouses,
  removeRouteStop,
  reorderRouteStops,
  updateWarehouseRoute,
} from "../api/client";
import type { DestinationLocation, Warehouse, WarehouseRoute } from "../api/types";
import { Button, Card, Input, Select, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";
import { ColorSwatchPicker } from "../components/ColorSwatchPicker";
import { RouteMap } from "../components/RouteMap";

export default function WarehouseRoutesPage() {
  const tenantId = getTenantId();

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState("");
  const [routes, setRoutes] = useState<WarehouseRoute[]>([]);
  const [destinations, setDestinations] = useState<DestinationLocation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [newRouteName, setNewRouteName] = useState("");
  const [newRouteColor, setNewRouteColor] = useState("");
  const [editingRouteId, setEditingRouteId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ name: "", color: "" });
  const [openRouteId, setOpenRouteId] = useState<string | null>(null);
  const [selectedDestinationIds, setSelectedDestinationIds] = useState<Set<string>>(new Set());

  // Routes only make sense for warehouses actually in use — a warehouse
  // that exists locally but hasn't been opted into sync isn't a real
  // operating location yet (see DECISIONS.md). Looking `selectedWarehouse`
  // up from this filtered list too (not the raw `warehouses` array) means
  // a warehouse that gets un-synced while selected correctly falls back
  // to "nothing selected" rather than continuing to show its routes.
  const syncedWarehouses = warehouses.filter((w) => w.is_synced);
  const selectedWarehouse = syncedWarehouses.find((w) => w.id === selectedWarehouseId) ?? null;

  useEffect(() => {
    if (!tenantId) return;
    listWarehouses(tenantId).then(setWarehouses).catch(() => {});
    listDestinationLocations(tenantId).then(setDestinations).catch(() => {});
  }, [tenantId]);

  function loadRoutes(warehouseId: string) {
    if (!tenantId || !warehouseId) {
      setRoutes([]);
      return;
    }
    listWarehouseRoutes(tenantId, warehouseId).then(setRoutes).catch(() => setRoutes([]));
  }

  useEffect(() => {
    loadRoutes(selectedWarehouseId);
    setOpenRouteId(null);
    setSelectedDestinationIds(new Set());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedWarehouseId, tenantId]);

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  async function handleCreateRoute(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createWarehouseRoute(tenantId!, selectedWarehouseId, {
        name: newRouteName,
        color: newRouteColor || null,
      });
      setNewRouteName("");
      setNewRouteColor("");
      loadRoutes(selectedWarehouseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create route");
    }
  }

  function handleStartEdit(route: WarehouseRoute) {
    setEditingRouteId(route.id);
    setEditForm({ name: route.name, color: route.color });
  }

  async function handleSaveEdit(routeId: string) {
    setError(null);
    try {
      await updateWarehouseRoute(tenantId!, selectedWarehouseId, routeId, editForm);
      setEditingRouteId(null);
      loadRoutes(selectedWarehouseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update route");
    }
  }

  async function handleDeleteRoute(route: WarehouseRoute) {
    setError(null);
    try {
      await deleteWarehouseRoute(tenantId!, selectedWarehouseId, route.id);
      if (openRouteId === route.id) setOpenRouteId(null);
      loadRoutes(selectedWarehouseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete route");
    }
  }

  function handleToggleOpen(routeId: string) {
    setOpenRouteId((prev) => (prev === routeId ? null : routeId));
    setSelectedDestinationIds(new Set());
  }

  function handleToggleDestinationSelect(id: string) {
    setSelectedDestinationIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkAdd(route: WarehouseRoute) {
    setError(null);
    try {
      const result = await bulkAddRouteStops(
        tenantId!,
        selectedWarehouseId,
        route.id,
        Array.from(selectedDestinationIds),
      );
      setSelectedDestinationIds(new Set());
      loadRoutes(selectedWarehouseId);
      if (result.skipped_destination_ids.length > 0) {
        setError(
          `${result.skipped_destination_ids.length} destination(s) were already in this route and were skipped.`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add destinations");
    }
  }

  async function handleReorder(route: WarehouseRoute, index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= route.stops.length) return;
    const ids = route.stops.map((s) => s.destination.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setError(null);
    try {
      await reorderRouteStops(tenantId!, selectedWarehouseId, route.id, ids);
      loadRoutes(selectedWarehouseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reorder stops");
    }
  }

  async function handleRemoveStop(route: WarehouseRoute, destinationId: string) {
    setError(null);
    try {
      await removeRouteStop(tenantId!, selectedWarehouseId, route.id, destinationId);
      loadRoutes(selectedWarehouseId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove stop");
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Routes</h1>
      <p className="mb-6 text-sm text-text-muted">
        Arrange each warehouse's delivery routes — an ordered, colored sequence of stops from the
        destination library. Straight lines on the map, not real road routing.
      </p>

      <div className="mb-6 max-w-xs">
        <Select
          label="Warehouse"
          value={selectedWarehouseId}
          onChange={(e) => setSelectedWarehouseId(e.target.value)}
        >
          <option value="">Choose a warehouse...</option>
          {syncedWarehouses.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </Select>
      </div>

      {syncedWarehouses.length === 0 && (
        <p className="text-sm text-text-muted">
          No synced warehouses yet —{" "}
          <Link
            to="/warehouses"
            className="rounded-sm text-accent underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            sync one on the Warehouses page
          </Link>{" "}
          first.
        </p>
      )}

      {syncedWarehouses.length > 0 && !selectedWarehouse && (
        <p className="text-sm text-text-muted">Choose a warehouse to manage its routes.</p>
      )}

      {selectedWarehouse && (
        <>
          {selectedWarehouse.lat == null || selectedWarehouse.lng == null ? (
            <Card className="mb-6">
              <p className="text-sm text-text-muted">
                This warehouse has no coordinates set —{" "}
                <Link
                  to="/warehouses"
                  className="rounded-sm text-accent underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
                >
                  set them on the Warehouses page
                </Link>{" "}
                to see the map and per-stop distances.
              </p>
            </Card>
          ) : (
            <div className="mb-6">
              <RouteMap
                key={selectedWarehouse.id}
                warehouse={{
                  name: selectedWarehouse.name,
                  lat: selectedWarehouse.lat,
                  lng: selectedWarehouse.lng,
                }}
                routes={routes}
              />
            </div>
          )}

          <Card heading="Create a route" className="mb-6">
            <form onSubmit={handleCreateRoute} className="flex flex-wrap items-end gap-4">
              <Input
                label="Name"
                value={newRouteName}
                onChange={(e) => setNewRouteName(e.target.value)}
                required
              />
              <ColorSwatchPicker label="Color (optional)" value={newRouteColor} onChange={setNewRouteColor} />
              <Button type="submit">Create route</Button>
            </form>
          </Card>

          {error && <p className="mb-4 text-sm text-status-full">{error}</p>}

          {routes.length === 0 ? (
            <p className="text-sm text-text-muted">No routes yet for this warehouse — create one above.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {routes.map((route) => {
                const availableDestinations = destinations.filter(
                  (d) => !route.stops.some((s) => s.destination.id === d.id),
                );
                return (
                  <Card key={route.id}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <span
                          className="inline-block h-4 w-4 rounded-full"
                          style={{ backgroundColor: route.color }}
                        />
                        {editingRouteId === route.id ? (
                          <div className="flex items-center gap-2">
                            <Input
                              value={editForm.name}
                              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                            />
                            <ColorSwatchPicker
                              value={editForm.color}
                              onChange={(color) => setEditForm({ ...editForm, color })}
                            />
                            <Button size="sm" onClick={() => handleSaveEdit(route.id)}>
                              Save
                            </Button>
                            <Button size="sm" variant="secondary" onClick={() => setEditingRouteId(null)}>
                              Cancel
                            </Button>
                          </div>
                        ) : (
                          <>
                            <span className="font-medium text-text">{route.name}</span>
                            <span className="text-sm text-text-muted">
                              {route.stops.length} stop{route.stops.length === 1 ? "" : "s"}
                            </span>
                          </>
                        )}
                      </div>
                      {editingRouteId !== route.id && (
                        <div className="flex gap-2">
                          <Button size="sm" variant="secondary" onClick={() => handleToggleOpen(route.id)}>
                            {openRouteId === route.id ? "Close" : "Manage stops"}
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => handleStartEdit(route)}>
                            Rename / recolor
                          </Button>
                          <Button size="sm" variant="secondary" onClick={() => handleDeleteRoute(route)}>
                            Delete
                          </Button>
                        </div>
                      )}
                    </div>

                    {openRouteId === route.id && (
                      <div className="mt-4 border-t border-border pt-4">
                        {route.stops.length === 0 ? (
                          <p className="mb-4 text-sm text-text-muted">No stops yet — add some below.</p>
                        ) : (
                          <Table>
                            <TableHead>
                              <TableRow>
                                <Th>#</Th>
                                <Th>Destination</Th>
                                <Th>Distance (km)</Th>
                                <Th>Actions</Th>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {route.stops.map((stop, index) => (
                                <TableRow key={stop.id}>
                                  <Td>{index + 1}</Td>
                                  <Td className="font-medium">{stop.destination.name}</Td>
                                  <Td>{stop.distance_km != null ? stop.distance_km.toFixed(1) : "—"}</Td>
                                  <Td>
                                    <div className="flex gap-1">
                                      <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => handleReorder(route, index, -1)}
                                        disabled={index === 0}
                                      >
                                        ↑
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => handleReorder(route, index, 1)}
                                        disabled={index === route.stops.length - 1}
                                      >
                                        ↓
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => handleRemoveStop(route, stop.destination.id)}
                                      >
                                        Remove
                                      </Button>
                                    </div>
                                  </Td>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        )}

                        <div className="mt-4">
                          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
                            Add destinations to this route
                          </p>
                          {availableDestinations.length === 0 ? (
                            <p className="text-sm text-text-muted">
                              Every destination is already in this route.
                            </p>
                          ) : (
                            <div className="mb-2 flex max-h-48 flex-col gap-1 overflow-y-auto">
                              {availableDestinations.map((d) => (
                                <label key={d.id} className="flex items-center gap-2 text-sm text-text">
                                  <input
                                    type="checkbox"
                                    checked={selectedDestinationIds.has(d.id)}
                                    onChange={() => handleToggleDestinationSelect(d.id)}
                                    className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                                  />
                                  {d.name}
                                </label>
                              ))}
                            </div>
                          )}
                          <Button
                            size="sm"
                            onClick={() => handleBulkAdd(route)}
                            disabled={selectedDestinationIds.size === 0}
                          >
                            Add {selectedDestinationIds.size > 0 ? selectedDestinationIds.size : ""} selected
                          </Button>
                        </div>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
