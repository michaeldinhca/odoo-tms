import { type FormEvent, useEffect, useState } from "react";
import {
  addWarehouseDestinationLocation,
  createDestinationLocation,
  deleteDestinationLocation,
  getTenantId,
  listDestinationLocations,
  listWarehouseDestinationLocations,
  listWarehouses,
  removeWarehouseDestinationLocation,
  setWarehouseCoordinates,
  updateDestinationLocation,
} from "../api/client";
import type {
  DestinationLocation,
  DestinationLocationInput,
  Warehouse,
  WarehouseDestinationLocation,
} from "../api/types";
import { Button, Card, Input, Select, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";

const EMPTY_FORM: DestinationLocationInput = {
  name: "",
  street: "",
  street2: "",
  city: "",
  state: "",
  country: "",
  zip: "",
  lat: 0,
  lng: 0,
};

function formatAddress(d: DestinationLocation): string {
  const parts = [[d.street, d.street2].filter(Boolean).join(", "), d.city, d.zip, d.country].filter(
    Boolean,
  );
  return parts.length > 0 ? parts.join(", ") : "—";
}

export default function DestinationLocationsPage() {
  const tenantId = getTenantId();

  const [destinations, setDestinations] = useState<DestinationLocation[]>([]);
  const [form, setForm] = useState<DestinationLocationInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [libraryError, setLibraryError] = useState<string | null>(null);

  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>("");
  const [routeSet, setRouteSet] = useState<WarehouseDestinationLocation[]>([]);
  const [coordsForm, setCoordsForm] = useState<{ lat: string; lng: string }>({ lat: "", lng: "" });
  const [addDestinationId, setAddDestinationId] = useState<string>("");
  const [routeSetError, setRouteSetError] = useState<string | null>(null);

  const selectedWarehouse = warehouses.find((w) => w.id === selectedWarehouseId) ?? null;

  function loadDestinations() {
    if (!tenantId) return;
    listDestinationLocations(tenantId).then(setDestinations).catch(() => {});
  }

  useEffect(loadDestinations, [tenantId]);

  useEffect(() => {
    if (!tenantId) return;
    listWarehouses(tenantId).then(setWarehouses).catch(() => {});
  }, [tenantId]);

  function loadRouteSet(warehouseId: string) {
    if (!tenantId || !warehouseId) {
      setRouteSet([]);
      return;
    }
    listWarehouseDestinationLocations(tenantId, warehouseId)
      .then(setRouteSet)
      .catch(() => setRouteSet([]));
  }

  useEffect(() => {
    loadRouteSet(selectedWarehouseId);
    const warehouse = warehouses.find((w) => w.id === selectedWarehouseId);
    setCoordsForm({
      lat: warehouse?.lat != null ? String(warehouse.lat) : "",
      lng: warehouse?.lng != null ? String(warehouse.lng) : "",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedWarehouseId, tenantId]);

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLibraryError(null);
    try {
      if (editingId) {
        const updated = await updateDestinationLocation(tenantId!, editingId, form);
        setDestinations((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      } else {
        const created = await createDestinationLocation(tenantId!, form);
        setDestinations((prev) => [...prev, created]);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
    } catch (err) {
      setLibraryError(err instanceof Error ? err.message : "Failed to save destination");
    }
  }

  function handleEdit(destination: DestinationLocation) {
    setEditingId(destination.id);
    setForm({
      name: destination.name,
      street: destination.street,
      street2: destination.street2,
      city: destination.city,
      state: destination.state,
      country: destination.country,
      zip: destination.zip,
      lat: destination.lat,
      lng: destination.lng,
    });
  }

  function handleCancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleDelete(destination: DestinationLocation) {
    setLibraryError(null);
    try {
      await deleteDestinationLocation(tenantId!, destination.id);
      setDestinations((prev) => prev.filter((d) => d.id !== destination.id));
      // The delete may have removed this destination from the currently
      // viewed warehouse's route set too.
      if (selectedWarehouseId) loadRouteSet(selectedWarehouseId);
    } catch (err) {
      setLibraryError(err instanceof Error ? err.message : "Failed to delete destination");
    }
  }

  async function handleSaveCoordinates(event: FormEvent) {
    event.preventDefault();
    if (!selectedWarehouseId) return;
    setRouteSetError(null);
    try {
      const updated = await setWarehouseCoordinates(tenantId!, selectedWarehouseId, {
        lat: coordsForm.lat ? Number(coordsForm.lat) : null,
        lng: coordsForm.lng ? Number(coordsForm.lng) : null,
      });
      setWarehouses((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
      loadRouteSet(selectedWarehouseId);
    } catch (err) {
      setRouteSetError(err instanceof Error ? err.message : "Failed to save coordinates");
    }
  }

  async function handleAddDestination() {
    if (!selectedWarehouseId || !addDestinationId) return;
    setRouteSetError(null);
    try {
      await addWarehouseDestinationLocation(tenantId!, selectedWarehouseId, addDestinationId);
      setAddDestinationId("");
      loadRouteSet(selectedWarehouseId);
    } catch (err) {
      setRouteSetError(err instanceof Error ? err.message : "Failed to add destination");
    }
  }

  async function handleRemoveFromRouteSet(destinationId: string) {
    if (!selectedWarehouseId) return;
    setRouteSetError(null);
    try {
      await removeWarehouseDestinationLocation(tenantId!, selectedWarehouseId, destinationId);
      loadRouteSet(selectedWarehouseId);
    } catch (err) {
      setRouteSetError(err instanceof Error ? err.message : "Failed to remove destination");
    }
  }

  const routeSetIds = new Set(routeSet.map((r) => r.destination.id));
  const availableToAdd = destinations.filter((d) => !routeSetIds.has(d.id));

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Destination Locations</h1>
      <p className="mb-6 text-sm text-text-muted">
        A reusable library of delivery destinations. Attach a destination to any number of
        warehouses' route sets — the distance shown is computed from each warehouse's coordinates.
      </p>

      <Card heading="Add a destination" className="mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Input
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <Input
              label="Street"
              value={form.street}
              onChange={(e) => setForm({ ...form, street: e.target.value })}
            />
            <Input
              label="City"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
            <Input
              label="State"
              value={form.state}
              onChange={(e) => setForm({ ...form, state: e.target.value })}
            />
            <Input
              label="Country"
              value={form.country}
              onChange={(e) => setForm({ ...form, country: e.target.value })}
            />
            <Input
              label="Zip"
              value={form.zip}
              onChange={(e) => setForm({ ...form, zip: e.target.value })}
            />
            <Input
              label="Latitude"
              type="number"
              step="any"
              value={form.lat}
              onChange={(e) => setForm({ ...form, lat: Number(e.target.value) })}
              required
            />
            <Input
              label="Longitude"
              type="number"
              step="any"
              value={form.lng}
              onChange={(e) => setForm({ ...form, lng: Number(e.target.value) })}
              required
            />
          </div>
          {libraryError && <p className="text-sm text-status-full">{libraryError}</p>}
          <div className="flex gap-2">
            <Button type="submit">{editingId ? "Save changes" : "Add destination"}</Button>
            {editingId && (
              <Button type="button" variant="secondary" onClick={handleCancelEdit}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </Card>

      {destinations.length === 0 ? (
        <p className="mb-6 text-sm text-text-muted">No destinations yet — add one above.</p>
      ) : (
        <div className="mb-6">
          <Table>
            <TableHead>
              <TableRow>
                <Th>Name</Th>
                <Th>Address</Th>
                <Th>Lat</Th>
                <Th>Lng</Th>
                <Th>Actions</Th>
              </TableRow>
            </TableHead>
            <TableBody>
              {destinations.map((d) => (
                <TableRow key={d.id}>
                  <Td className="font-medium">{d.name}</Td>
                  <Td>{formatAddress(d)}</Td>
                  <Td>{d.lat}</Td>
                  <Td>{d.lng}</Td>
                  <Td>
                    <div className="flex gap-2">
                      <Button size="sm" variant="secondary" onClick={() => handleEdit(d)}>
                        Edit
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => handleDelete(d)}>
                        Delete
                      </Button>
                    </div>
                  </Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Card heading="Warehouse route set">
        <div className="mb-4 max-w-xs">
          <Select
            label="Warehouse"
            value={selectedWarehouseId}
            onChange={(e) => setSelectedWarehouseId(e.target.value)}
          >
            <option value="">Choose a warehouse...</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </Select>
        </div>

        {selectedWarehouse && (
          <>
            <form onSubmit={handleSaveCoordinates} className="mb-4 flex flex-wrap items-end gap-4">
              <Input
                label="Warehouse latitude"
                type="number"
                step="any"
                value={coordsForm.lat}
                onChange={(e) => setCoordsForm({ ...coordsForm, lat: e.target.value })}
              />
              <Input
                label="Warehouse longitude"
                type="number"
                step="any"
                value={coordsForm.lng}
                onChange={(e) => setCoordsForm({ ...coordsForm, lng: e.target.value })}
              />
              <Button type="submit" size="sm">
                Save coordinates
              </Button>
            </form>
            {!selectedWarehouse.lat && (
              <p className="mb-4 text-sm text-text-muted">
                Set this warehouse's coordinates to see distances below.
              </p>
            )}

            <div className="mb-4 flex flex-wrap items-end gap-4">
              <div className="max-w-xs flex-1">
                <Select
                  label="Add destination to route set"
                  value={addDestinationId}
                  onChange={(e) => setAddDestinationId(e.target.value)}
                >
                  <option value="">Choose a destination...</option>
                  {availableToAdd.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </Select>
              </div>
              <Button size="sm" onClick={handleAddDestination} disabled={!addDestinationId}>
                Add
              </Button>
            </div>
            {routeSetError && <p className="mb-4 text-sm text-status-full">{routeSetError}</p>}

            {routeSet.length === 0 ? (
              <p className="text-sm text-text-muted">No destinations in this warehouse's route set yet.</p>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <Th>Name</Th>
                    <Th>Address</Th>
                    <Th>Distance (km)</Th>
                    <Th>Actions</Th>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {routeSet.map((r) => (
                    <TableRow key={r.id}>
                      <Td className="font-medium">{r.destination.name}</Td>
                      <Td>{formatAddress(r.destination)}</Td>
                      <Td>{r.distance_km != null ? r.distance_km.toFixed(1) : "—"}</Td>
                      <Td>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleRemoveFromRouteSet(r.destination.id)}
                        >
                          Remove
                        </Button>
                      </Td>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
