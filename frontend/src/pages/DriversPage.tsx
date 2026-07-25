import { type FormEvent, useEffect, useState } from "react";
import {
  createDriver,
  deleteDriver,
  getTenantId,
  linkDriverToOdoo,
  listDrivers,
  listOdooEmployees,
  listVehicles,
  unlinkDriverFromOdoo,
  updateDriver,
} from "../api/client";
import type {
  Driver,
  DriverInput,
  DriverStatus,
  FleetVehicle,
  OdooEmployeeOption,
} from "../api/types";
import { useOdooInstance } from "../context/OdooInstanceContext";

const EMPTY_FORM: DriverInput = {
  name: "",
  phone: "",
  email: "",
  license_number: "",
  id_passport_number: "",
  status: "active",
  assigned_vehicle_id: null,
};

export default function DriversPage() {
  const tenantId = getTenantId();
  const { isActive } = useOdooInstance();
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [vehicles, setVehicles] = useState<FleetVehicle[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [form, setForm] = useState<DriverInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [odooEmployees, setOdooEmployees] = useState<OdooEmployeeOption[] | null>(null);
  const [odooAvailable, setOdooAvailable] = useState(true);
  const [linkingId, setLinkingId] = useState<string | null>(null);
  const [selectedOdooId, setSelectedOdooId] = useState<string>("");

  function loadDrivers() {
    if (!tenantId) return;
    listDrivers(tenantId, showArchived).then(setDrivers).catch(() => {});
  }

  useEffect(loadDrivers, [tenantId, showArchived]);

  useEffect(() => {
    if (!tenantId) return;
    // Only active vehicles are offered for assignment — an archived vehicle
    // shouldn't be pickable for a new driver.
    listVehicles(tenantId).then(setVehicles).catch(() => {});
  }, [tenantId]);

  if (!tenantId) return <p className="page">Not logged in.</p>;

  function vehicleName(id: string | null): string {
    if (!id) return "—";
    return vehicles.find((v) => v.id === id)?.name ?? id;
  }

  function odooEmployeeName(id: number | null): string {
    if (id === null) return "—";
    const match = odooEmployees?.find((e) => e.id === id);
    return match ? match.name : `Odoo #${id}`;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      if (editingId) {
        const updated = await updateDriver(tenantId!, editingId, form);
        setDrivers((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      } else {
        const created = await createDriver(tenantId!, form);
        setDrivers((prev) => [...prev, created]);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save driver");
    }
  }

  function handleEdit(driver: Driver) {
    setEditingId(driver.id);
    setForm({
      name: driver.name,
      phone: driver.phone,
      email: driver.email,
      license_number: driver.license_number,
      id_passport_number: driver.id_passport_number,
      status: driver.status,
      assigned_vehicle_id: driver.assigned_vehicle_id,
    });
  }

  function handleCancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleDelete(driver: Driver) {
    setError(null);
    try {
      await deleteDriver(tenantId!, driver.id);
      setDrivers((prev) => prev.filter((d) => d.id !== driver.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete driver");
    }
  }

  async function handleStartLink(driver: Driver) {
    setError(null);
    setLinkingId(driver.id);
    setSelectedOdooId(driver.odoo_employee_id ? String(driver.odoo_employee_id) : "");
    if (odooEmployees === null) {
      try {
        const result = await listOdooEmployees(tenantId!);
        setOdooAvailable(result.available);
        setOdooEmployees(result.employees);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load Odoo employees");
      }
    }
  }

  async function handleConfirmLink(driver: Driver) {
    setError(null);
    try {
      const updated = await linkDriverToOdoo(tenantId!, driver.id, Number(selectedOdooId));
      setDrivers((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      setLinkingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to link driver");
    }
  }

  async function handleUnlink(driver: Driver) {
    setError(null);
    try {
      const updated = await unlinkDriverFromOdoo(tenantId!, driver.id);
      setDrivers((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink driver");
    }
  }

  async function handleArchiveToggle(driver: Driver) {
    setError(null);
    try {
      await updateDriver(tenantId!, driver.id, { active: !driver.active });
      loadDrivers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update archive state");
    }
  }

  return (
    <div className="page">
      <h1>Drivers</h1>
      <p className="hint">
        Drivers live here, not in Odoo. Linking to an Odoo hr.employee is just a reference
        pointer and never overwrites the fields below.
      </p>

      <form onSubmit={handleSubmit}>
        <label>
          Name
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </label>
        <label>
          Phone
          <input
            value={form.phone ?? ""}
            onChange={(e) => setForm({ ...form, phone: e.target.value || null })}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={form.email ?? ""}
            onChange={(e) => setForm({ ...form, email: e.target.value || null })}
          />
        </label>
        <label>
          License number
          <input
            value={form.license_number ?? ""}
            onChange={(e) => setForm({ ...form, license_number: e.target.value || null })}
          />
        </label>
        <label>
          Assigned vehicle
          <select
            value={form.assigned_vehicle_id ?? ""}
            onChange={(e) => setForm({ ...form, assigned_vehicle_id: e.target.value || null })}
          >
            <option value="">None</option>
            {vehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value as DriverStatus })}
          >
            <option value="active">Active</option>
            <option value="locked">Locked</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button type="submit">{editingId ? "Save changes" : "Add driver"}</button>
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
            <th>Status</th>
            <th>Phone</th>
            <th>Assigned vehicle</th>
            <th>Odoo link</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {drivers.map((driver) => (
            <tr key={driver.id}>
              <td>{driver.name}</td>
              <td>{driver.status}</td>
              <td>{driver.phone ?? "—"}</td>
              <td>{vehicleName(driver.assigned_vehicle_id)}</td>
              <td>
                {driver.odoo_link_status === "linked" ? (
                  <>
                    Linked — {odooEmployeeName(driver.odoo_employee_id)}
                    <button type="button" onClick={() => handleUnlink(driver)}>
                      Unlink
                    </button>
                  </>
                ) : !isActive ? (
                  <span className="hint">Connect Odoo to link drivers.</span>
                ) : linkingId === driver.id ? (
                  odooEmployees && !odooAvailable ? (
                    <span className="hint">HR module not available on this Odoo instance.</span>
                  ) : (
                    <>
                      <select value={selectedOdooId} onChange={(e) => setSelectedOdooId(e.target.value)}>
                        <option value="">Choose...</option>
                        {(odooEmployees ?? []).map((e) => (
                          <option key={e.id} value={e.id}>
                            {e.name}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => handleConfirmLink(driver)}
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
                  <button type="button" onClick={() => handleStartLink(driver)}>
                    Link to Odoo Employee
                  </button>
                )}
              </td>
              <td>
                <button type="button" onClick={() => handleEdit(driver)}>
                  Edit
                </button>
                <button type="button" onClick={() => handleArchiveToggle(driver)}>
                  {driver.active ? "Archive" : "Unarchive"}
                </button>
                <button type="button" onClick={() => handleDelete(driver)}>
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
