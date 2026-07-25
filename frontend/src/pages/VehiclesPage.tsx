import { type FormEvent, useEffect, useState } from "react";
import {
  createVehicle,
  deleteVehicle,
  getTenantId,
  linkVehicleToOdoo,
  listOdooFleetVehicles,
  listVehicles,
  listWarehouses,
  unlinkVehicleFromOdoo,
  updateVehicle,
} from "../api/client";
import type {
  FleetVehicle,
  FleetVehicleInput,
  FleetVehicleStatus,
  FleetVehicleType,
  OdooFleetVehicleOption,
  Warehouse,
} from "../api/types";
import {
  Badge,
  type BadgeVariant,
  Button,
  Card,
  Input,
  Select,
  Table,
  TableBody,
  TableHead,
  TableRow,
  Td,
  Th,
} from "../components/ui";
import { useOdooInstance } from "../context/OdooInstanceContext";

const EMPTY_FORM: FleetVehicleInput = {
  name: "",
  license_plate: "",
  vehicle_type: "van",
  payload_capacity_kg: null,
  volume_capacity_m3: null,
  fuel_consumption_per_100km: null,
  home_warehouse_id: null,
  status: "active",
};

const STATUS_BADGE: Record<FleetVehicleStatus, BadgeVariant> = {
  active: "ok",
  maintenance: "warning",
  inactive: "neutral",
};

export default function VehiclesPage() {
  const tenantId = getTenantId();
  const { isActive } = useOdooInstance();
  const [vehicles, setVehicles] = useState<FleetVehicle[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [form, setForm] = useState<FleetVehicleInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [odooVehicles, setOdooVehicles] = useState<OdooFleetVehicleOption[] | null>(null);
  const [odooAvailable, setOdooAvailable] = useState(true);
  const [linkingId, setLinkingId] = useState<string | null>(null);
  const [selectedOdooId, setSelectedOdooId] = useState<string>("");

  function loadVehicles() {
    if (!tenantId) return;
    listVehicles(tenantId, showArchived).then(setVehicles).catch(() => {});
  }

  useEffect(loadVehicles, [tenantId, showArchived]);

  useEffect(() => {
    if (!tenantId) return;
    listWarehouses(tenantId).then(setWarehouses).catch(() => {});
  }, [tenantId]);

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  function warehouseName(id: string | null): string {
    if (!id) return "—";
    return warehouses.find((w) => w.id === id)?.name ?? id;
  }

  function odooVehicleName(id: number | null): string {
    if (id === null) return "—";
    const match = odooVehicles?.find((v) => v.id === id);
    return match ? `${match.name}${match.license_plate ? ` (${match.license_plate})` : ""}` : `Odoo #${id}`;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      if (editingId) {
        const updated = await updateVehicle(tenantId!, editingId, form);
        setVehicles((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
      } else {
        const created = await createVehicle(tenantId!, form);
        setVehicles((prev) => [...prev, created]);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save vehicle");
    }
  }

  function handleEdit(vehicle: FleetVehicle) {
    setEditingId(vehicle.id);
    setForm({
      name: vehicle.name,
      license_plate: vehicle.license_plate,
      vehicle_type: vehicle.vehicle_type,
      payload_capacity_kg: vehicle.payload_capacity_kg,
      volume_capacity_m3: vehicle.volume_capacity_m3,
      fuel_consumption_per_100km: vehicle.fuel_consumption_per_100km,
      home_warehouse_id: vehicle.home_warehouse_id,
      status: vehicle.status,
    });
  }

  function handleCancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleDelete(vehicle: FleetVehicle) {
    setError(null);
    try {
      await deleteVehicle(tenantId!, vehicle.id);
      setVehicles((prev) => prev.filter((v) => v.id !== vehicle.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete vehicle");
    }
  }

  async function handleStartLink(vehicle: FleetVehicle) {
    setError(null);
    setLinkingId(vehicle.id);
    setSelectedOdooId(vehicle.odoo_fleet_vehicle_id ? String(vehicle.odoo_fleet_vehicle_id) : "");
    if (odooVehicles === null) {
      try {
        const result = await listOdooFleetVehicles(tenantId!);
        setOdooAvailable(result.available);
        setOdooVehicles(result.vehicles);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load Odoo vehicles");
      }
    }
  }

  async function handleConfirmLink(vehicle: FleetVehicle) {
    setError(null);
    try {
      const updated = await linkVehicleToOdoo(tenantId!, vehicle.id, Number(selectedOdooId));
      setVehicles((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
      setLinkingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to link vehicle");
    }
  }

  async function handleUnlink(vehicle: FleetVehicle) {
    setError(null);
    try {
      const updated = await unlinkVehicleFromOdoo(tenantId!, vehicle.id);
      setVehicles((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink vehicle");
    }
  }

  async function handleArchiveToggle(vehicle: FleetVehicle) {
    setError(null);
    try {
      await updateVehicle(tenantId!, vehicle.id, { active: !vehicle.active });
      loadVehicles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update archive state");
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Vehicles</h1>
      <p className="mb-4 text-sm text-text-muted">
        Vehicles live here, not in Odoo — a vehicle can exist with no Odoo link at all (e.g. a
        subcontracted truck). Linking to an Odoo fleet.vehicle is just a reference pointer and
        never overwrites the fields below.
      </p>

      <Card className="mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Input
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <Input
              label="License plate"
              value={form.license_plate ?? ""}
              onChange={(e) => setForm({ ...form, license_plate: e.target.value || null })}
            />
            <Select
              label="Type"
              value={form.vehicle_type}
              onChange={(e) => setForm({ ...form, vehicle_type: e.target.value as FleetVehicleType })}
            >
              <option value="van">Van</option>
              <option value="truck">Truck</option>
              <option value="motorbike">Motorbike</option>
              <option value="three_wheeler">Three-wheeler</option>
              <option value="other">Other</option>
            </Select>
            <Input
              label="Payload capacity (kg)"
              type="number"
              value={form.payload_capacity_kg ?? ""}
              onChange={(e) =>
                setForm({ ...form, payload_capacity_kg: e.target.value ? Number(e.target.value) : null })
              }
            />
            <Select
              label="Home warehouse"
              value={form.home_warehouse_id ?? ""}
              onChange={(e) => setForm({ ...form, home_warehouse_id: e.target.value || null })}
            >
              <option value="">None</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </Select>
            <Select
              label="Status"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as FleetVehicleStatus })}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="maintenance">Maintenance</option>
            </Select>
          </div>
          {error && <p className="text-sm text-status-full">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit">{editingId ? "Save changes" : "Add vehicle"}</Button>
            {editingId && (
              <Button type="button" variant="secondary" onClick={handleCancelEdit}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </Card>

      <div className="mb-4">
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

      <Table>
        <TableHead>
          <TableRow>
            <Th>Name</Th>
            <Th>Type</Th>
            <Th>Status</Th>
            <Th>Payload (kg)</Th>
            <Th>Home warehouse</Th>
            <Th>Odoo link</Th>
            <Th>Actions</Th>
          </TableRow>
        </TableHead>
        <TableBody>
          {vehicles.map((vehicle) => (
            <TableRow key={vehicle.id}>
              <Td className="font-medium">{vehicle.name}</Td>
              <Td>{vehicle.vehicle_type}</Td>
              <Td>
                <Badge variant={STATUS_BADGE[vehicle.status]}>{vehicle.status}</Badge>
              </Td>
              <Td>{vehicle.payload_capacity_kg ?? "—"}</Td>
              <Td>{warehouseName(vehicle.home_warehouse_id)}</Td>
              <Td>
                {vehicle.odoo_link_status === "linked" ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="accent">Linked — {odooVehicleName(vehicle.odoo_fleet_vehicle_id)}</Badge>
                    <Button size="sm" variant="secondary" onClick={() => handleUnlink(vehicle)}>
                      Unlink
                    </Button>
                  </div>
                ) : !isActive ? (
                  <span className="text-sm text-text-muted">Connect Odoo to link vehicles.</span>
                ) : linkingId === vehicle.id ? (
                  odooVehicles && !odooAvailable ? (
                    <span className="text-sm text-text-muted">
                      Fleet module not available on this Odoo instance.
                    </span>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <Select value={selectedOdooId} onChange={(e) => setSelectedOdooId(e.target.value)}>
                        <option value="">Choose...</option>
                        {(odooVehicles ?? []).map((v) => (
                          <option key={v.id} value={v.id}>
                            {v.name} {v.license_plate ? `(${v.license_plate})` : ""}
                          </option>
                        ))}
                      </Select>
                      <Button
                        size="sm"
                        onClick={() => handleConfirmLink(vehicle)}
                        disabled={!selectedOdooId}
                      >
                        Confirm
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setLinkingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  )
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => handleStartLink(vehicle)}>
                    Link to Odoo Vehicle
                  </Button>
                )}
              </Td>
              <Td>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => handleEdit(vehicle)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleArchiveToggle(vehicle)}>
                    {vehicle.active ? "Archive" : "Unarchive"}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleDelete(vehicle)}>
                    Delete
                  </Button>
                </div>
              </Td>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
