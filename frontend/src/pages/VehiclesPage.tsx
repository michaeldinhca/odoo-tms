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

  if (!tenantId) return <p className="page">Not logged in.</p>;

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
    <div className="page">
      <h1>Vehicles</h1>
      <p className="hint">
        Vehicles live here, not in Odoo — a vehicle can exist with no Odoo link at all (e.g. a
        subcontracted truck). Linking to an Odoo fleet.vehicle is just a reference pointer and
        never overwrites the fields below.
      </p>

      <form onSubmit={handleSubmit}>
        <label>
          Name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </label>
        <label>
          License plate
          <input
            value={form.license_plate ?? ""}
            onChange={(e) => setForm({ ...form, license_plate: e.target.value || null })}
          />
        </label>
        <label>
          Type
          <select
            value={form.vehicle_type}
            onChange={(e) => setForm({ ...form, vehicle_type: e.target.value as FleetVehicleType })}
          >
            <option value="van">Van</option>
            <option value="truck">Truck</option>
            <option value="motorbike">Motorbike</option>
            <option value="three_wheeler">Three-wheeler</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>
          Payload capacity (kg)
          <input
            type="number"
            value={form.payload_capacity_kg ?? ""}
            onChange={(e) =>
              setForm({ ...form, payload_capacity_kg: e.target.value ? Number(e.target.value) : null })
            }
          />
        </label>
        <label>
          Home warehouse
          <select
            value={form.home_warehouse_id ?? ""}
            onChange={(e) => setForm({ ...form, home_warehouse_id: e.target.value || null })}
          >
            <option value="">None</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value as FleetVehicleStatus })}
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </label>
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button type="submit">{editingId ? "Save changes" : "Add vehicle"}</button>
          {editingId && (
            <button type="button" onClick={handleCancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="actions">
        <label>
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
          />{" "}
          Show archived
        </label>
      </div>

      <table className="route-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Status</th>
            <th>Payload (kg)</th>
            <th>Home warehouse</th>
            <th>Odoo link</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {vehicles.map((vehicle) => (
            <tr key={vehicle.id}>
              <td>{vehicle.name}</td>
              <td>{vehicle.vehicle_type}</td>
              <td>{vehicle.status}</td>
              <td>{vehicle.payload_capacity_kg ?? "—"}</td>
              <td>{warehouseName(vehicle.home_warehouse_id)}</td>
              <td>
                {vehicle.odoo_link_status === "linked" ? (
                  <>
                    Linked — {odooVehicleName(vehicle.odoo_fleet_vehicle_id)}
                    <button type="button" onClick={() => handleUnlink(vehicle)}>
                      Unlink
                    </button>
                  </>
                ) : !isActive ? (
                  <span className="hint">Connect Odoo to link vehicles.</span>
                ) : linkingId === vehicle.id ? (
                  odooVehicles && !odooAvailable ? (
                    <span className="hint">Fleet module not available on this Odoo instance.</span>
                  ) : (
                    <>
                      <select value={selectedOdooId} onChange={(e) => setSelectedOdooId(e.target.value)}>
                        <option value="">Choose...</option>
                        {(odooVehicles ?? []).map((v) => (
                          <option key={v.id} value={v.id}>
                            {v.name} {v.license_plate ? `(${v.license_plate})` : ""}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => handleConfirmLink(vehicle)}
                        disabled={!selectedOdooId}
                      >
                        Confirm
                      </button>
                      <button type="button" onClick={() => setLinkingId(null)}>
                        Cancel
                      </button>
                    </>
                  )
                ) : (
                  <button type="button" onClick={() => handleStartLink(vehicle)}>
                    Link to Odoo Vehicle
                  </button>
                )}
              </td>
              <td>
                <button type="button" onClick={() => handleEdit(vehicle)}>
                  Edit
                </button>
                <button type="button" onClick={() => handleArchiveToggle(vehicle)}>
                  {vehicle.active ? "Archive" : "Unarchive"}
                </button>
                <button type="button" onClick={() => handleDelete(vehicle)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
