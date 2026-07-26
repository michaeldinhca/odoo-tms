import { type FormEvent, useEffect, useState } from "react";
import {
  createDestinationLocation,
  deleteDestinationLocation,
  getTenantId,
  listDestinationLocations,
  listPickingAddressOptions,
  updateDestinationLocation,
} from "../api/client";
import type { DestinationLocation, DestinationLocationInput, PickingAddressOption } from "../api/types";
import { Badge, Button, Card, Input, Select, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";

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

  const [pickingOptions, setPickingOptions] = useState<PickingAddressOption[]>([]);
  const [prefillIndex, setPrefillIndex] = useState("");

  function loadDestinations() {
    if (!tenantId) return;
    listDestinationLocations(tenantId).then(setDestinations).catch(() => {});
  }

  useEffect(loadDestinations, [tenantId]);

  useEffect(() => {
    if (!tenantId) return;
    listPickingAddressOptions(tenantId).then(setPickingOptions).catch(() => {});
  }, [tenantId]);

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
      setPrefillIndex("");
    } catch (err) {
      setLibraryError(err instanceof Error ? err.message : "Failed to save destination");
    }
  }

  function handleEdit(destination: DestinationLocation) {
    setEditingId(destination.id);
    setPrefillIndex("");
    setForm({
      name: destination.name,
      street: destination.street,
      street2: destination.street2,
      city: destination.city,
      state: destination.state,
      country: destination.country,
      zip: destination.zip,
      // Auto-created destinations (see DECISIONS.md) start with no
      // coordinates — default the form to 0 rather than leaving it
      // unset, same starting point as adding a brand new destination.
      lat: destination.lat ?? 0,
      lng: destination.lng ?? 0,
    });
  }

  function handleCancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setPrefillIndex("");
  }

  function handlePrefillFromPicking(indexValue: string) {
    setPrefillIndex(indexValue);
    if (!indexValue) return;
    const option = pickingOptions[Number(indexValue)];
    if (!option) return;
    setForm((prev) => ({
      ...prev,
      name: option.customer_name,
      street: option.street,
      street2: option.street2,
      city: option.city,
      state: option.state_name,
      country: option.country_name,
      zip: option.zip,
    }));
  }

  async function handleDelete(destination: DestinationLocation) {
    setLibraryError(null);
    try {
      await deleteDestinationLocation(tenantId!, destination.id);
      setDestinations((prev) => prev.filter((d) => d.id !== destination.id));
    } catch (err) {
      setLibraryError(err instanceof Error ? err.message : "Failed to delete destination");
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Destination Locations</h1>
      <p className="mb-6 text-sm text-text-muted">
        A reusable library of delivery destinations. Attach a destination to any number of
        warehouses' routes on the Routes page — the distance shown there is computed from each
        warehouse's coordinates (set on the Warehouses page).
      </p>

      <Card heading="Add a destination" className="mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {!editingId && pickingOptions.length > 0 && (
            <div className="max-w-sm">
              <Select
                label="Prefill from a recent delivery address"
                value={prefillIndex}
                onChange={(e) => handlePrefillFromPicking(e.target.value)}
              >
                <option value="">Type a new address...</option>
                {pickingOptions.map((option, index) => (
                  <option key={index} value={index}>
                    {option.customer_name} — {option.city || "no city"}
                  </option>
                ))}
              </Select>
            </div>
          )}
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
        <p className="text-sm text-text-muted">No destinations yet — add one above.</p>
      ) : (
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
            {destinations.map((d) => {
              const needsCoordinates = d.lat == null || d.lng == null;
              return (
                <TableRow key={d.id}>
                  <Td className="font-medium">
                    <div className="flex items-center gap-2">
                      {d.name}
                      {needsCoordinates && (
                        <Badge variant="warning" title="Auto-added from a delivery address — no coordinates yet">
                          Needs coordinates
                        </Badge>
                      )}
                    </div>
                  </Td>
                  <Td>{formatAddress(d)}</Td>
                  <Td>{d.lat ?? "—"}</Td>
                  <Td>{d.lng ?? "—"}</Td>
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
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
