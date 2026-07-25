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

const EMPTY_FORM: DriverInput = {
  name: "",
  phone: "",
  email: "",
  license_number: "",
  id_passport_number: "",
  status: "active",
  assigned_vehicle_id: null,
};

const STATUS_BADGE: Record<DriverStatus, BadgeVariant> = {
  active: "ok",
  locked: "warning",
  inactive: "neutral",
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

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

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
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Drivers</h1>
      <p className="mb-4 text-sm text-text-muted">
        Drivers live here, not in Odoo. Linking to an Odoo hr.employee is just a reference
        pointer and never overwrites the fields below.
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
              label="Phone"
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value || null })}
            />
            <Input
              label="Email"
              type="email"
              value={form.email ?? ""}
              onChange={(e) => setForm({ ...form, email: e.target.value || null })}
            />
            <Input
              label="License number"
              value={form.license_number ?? ""}
              onChange={(e) => setForm({ ...form, license_number: e.target.value || null })}
            />
            <Select
              label="Assigned vehicle"
              value={form.assigned_vehicle_id ?? ""}
              onChange={(e) => setForm({ ...form, assigned_vehicle_id: e.target.value || null })}
            >
              <option value="">None</option>
              {vehicles.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </Select>
            <Select
              label="Status"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as DriverStatus })}
            >
              <option value="active">Active</option>
              <option value="locked">Locked</option>
              <option value="inactive">Inactive</option>
            </Select>
          </div>
          {error && <p className="text-sm text-status-full">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit">{editingId ? "Save changes" : "Add driver"}</Button>
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
            <Th>Status</Th>
            <Th>Phone</Th>
            <Th>Assigned vehicle</Th>
            <Th>Odoo link</Th>
            <Th>Actions</Th>
          </TableRow>
        </TableHead>
        <TableBody>
          {drivers.map((driver) => (
            <TableRow key={driver.id}>
              <Td className="font-medium">{driver.name}</Td>
              <Td>
                <Badge variant={STATUS_BADGE[driver.status]}>{driver.status}</Badge>
              </Td>
              <Td>{driver.phone ?? "—"}</Td>
              <Td>{vehicleName(driver.assigned_vehicle_id)}</Td>
              <Td>
                {driver.odoo_link_status === "linked" ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="accent">Linked — {odooEmployeeName(driver.odoo_employee_id)}</Badge>
                    <Button size="sm" variant="secondary" onClick={() => handleUnlink(driver)}>
                      Unlink
                    </Button>
                  </div>
                ) : !isActive ? (
                  <span className="text-sm text-text-muted">Connect Odoo to link drivers.</span>
                ) : linkingId === driver.id ? (
                  odooEmployees && !odooAvailable ? (
                    <span className="text-sm text-text-muted">
                      HR module not available on this Odoo instance.
                    </span>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <Select value={selectedOdooId} onChange={(e) => setSelectedOdooId(e.target.value)}>
                        <option value="">Choose...</option>
                        {(odooEmployees ?? []).map((e) => (
                          <option key={e.id} value={e.id}>
                            {e.name}
                          </option>
                        ))}
                      </Select>
                      <Button
                        size="sm"
                        onClick={() => handleConfirmLink(driver)}
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
                  <Button size="sm" variant="secondary" onClick={() => handleStartLink(driver)}>
                    Link to Odoo Employee
                  </Button>
                )}
              </Td>
              <Td>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => handleEdit(driver)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleArchiveToggle(driver)}>
                    {driver.active ? "Archive" : "Unarchive"}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => handleDelete(driver)}>
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
