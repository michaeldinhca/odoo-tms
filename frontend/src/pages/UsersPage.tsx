import { type FormEvent, useEffect, useState } from "react";
import {
  createUser,
  deleteUser,
  getTenantId,
  listUsers,
  resetUserPassword,
  updateUser,
} from "../api/client";
import type { User, UserCreateInput, UserRole, UserUpdateInput } from "../api/types";
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
import { useCurrentUser } from "../context/CurrentUserContext";
import type { PermissionFlag } from "../context/CurrentUserContext";

const PERMISSION_FIELDS: { key: PermissionFlag; label: string; shortLabel: string }[] = [
  { key: "can_manage_connection", label: "Manage Odoo connection", shortLabel: "Connection" },
  { key: "can_manage_warehouses", label: "Manage warehouses", shortLabel: "Warehouses" },
  {
    key: "can_manage_operation_types",
    label: "Manage operation types",
    shortLabel: "Op. types",
  },
  {
    key: "can_manage_fleet",
    label: "Manage fleet (vehicles & drivers)",
    shortLabel: "Fleet",
  },
  {
    key: "can_run_planning",
    label: "Run planning (load stock pickings)",
    shortLabel: "Run planning",
  },
  { key: "can_use_load_planning", label: "Use load planning board", shortLabel: "Load planning" },
];

const EMPTY_FORM: UserCreateInput = {
  email: "",
  password: "",
  role: "user",
  can_manage_connection: false,
  can_manage_warehouses: false,
  can_manage_operation_types: false,
  can_manage_fleet: false,
  can_run_planning: true,
  can_use_load_planning: true,
};

const ROLE_BADGE: Record<UserRole, BadgeVariant> = {
  admin: "accent",
  user: "neutral",
};

export default function UsersPage() {
  const tenantId = getTenantId();
  const { user: me, refetch: refetchMe } = useCurrentUser();
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState<UserCreateInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [resettingId, setResettingId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");

  function load() {
    if (!tenantId) return;
    listUsers(tenantId).then(setUsers).catch(() => {});
  }

  useEffect(load, [tenantId]);

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      if (editingId) {
        const updatePayload: UserUpdateInput = {
          email: form.email,
          role: form.role,
          can_manage_connection: form.can_manage_connection,
          can_manage_warehouses: form.can_manage_warehouses,
          can_manage_operation_types: form.can_manage_operation_types,
          can_manage_fleet: form.can_manage_fleet,
          can_run_planning: form.can_run_planning,
          can_use_load_planning: form.can_use_load_planning,
        };
        const updated = await updateUser(tenantId!, editingId, updatePayload);
        setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
        if (updated.id === me?.id) refetchMe();
      } else {
        const created = await createUser(tenantId!, form);
        setUsers((prev) => [...prev, created]);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save user");
    }
  }

  function handleEdit(user: User) {
    setEditingId(user.id);
    setForm({
      email: user.email,
      password: "",
      role: user.role,
      can_manage_connection: user.can_manage_connection,
      can_manage_warehouses: user.can_manage_warehouses,
      can_manage_operation_types: user.can_manage_operation_types,
      can_manage_fleet: user.can_manage_fleet,
      can_run_planning: user.can_run_planning,
      can_use_load_planning: user.can_use_load_planning,
    });
  }

  function handleCancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleDelete(user: User) {
    setError(null);
    try {
      await deleteUser(tenantId!, user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete user");
    }
  }

  async function handleConfirmReset(user: User) {
    setError(null);
    try {
      await resetUserPassword(tenantId!, user.id, { new_password: newPassword });
      setResettingId(null);
      setNewPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Users</h1>
      <p className="mb-4 text-sm text-text-muted">
        Admin role only gates this page — every other feature is controlled by the individual
        permissions below, for admins and regular users alike. There's no invite-email flow yet,
        so set an initial password here and share it with the new user directly.
      </p>

      <Card className="mb-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Input
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
            <Input
              label={editingId ? "New password (leave blank to keep current)" : "Password"}
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              minLength={8}
              required={!editingId}
              disabled={!!editingId}
            />
            <Select
              label="Role"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </Select>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
              Permissions
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {PERMISSION_FIELDS.map((field) => (
                <label key={field.key} className="flex items-center gap-2 text-sm text-text">
                  <input
                    type="checkbox"
                    checked={form[field.key]}
                    onChange={(e) => setForm({ ...form, [field.key]: e.target.checked })}
                    className="h-4 w-4 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  />
                  {field.label}
                </label>
              ))}
            </div>
          </div>

          {editingId && form.password && (
            <p className="text-xs text-text-muted">
              This form doesn't change passwords — use "Reset password" in the table below for
              that. The password field here is disabled while editing.
            </p>
          )}
          {error && <p className="text-sm text-status-full">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit">{editingId ? "Save changes" : "Add user"}</Button>
            {editingId && (
              <Button type="button" variant="secondary" onClick={handleCancelEdit}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </Card>

      <Table>
        <TableHead>
          <TableRow>
            <Th>Email</Th>
            <Th>Role</Th>
            <Th>Permissions</Th>
            <Th>Actions</Th>
          </TableRow>
        </TableHead>
        <TableBody>
          {users.map((user) => (
            <TableRow key={user.id}>
              <Td className="font-medium">
                {user.email}
                {user.id === me?.id && <span className="ml-2 text-xs text-text-muted">(you)</span>}
              </Td>
              <Td>
                <Badge variant={ROLE_BADGE[user.role]}>{user.role}</Badge>
              </Td>
              <Td>
                <div className="flex flex-wrap gap-1">
                  {PERMISSION_FIELDS.filter((field) => user[field.key]).map((field) => (
                    <Badge key={field.key} variant="neutral">
                      {field.shortLabel}
                    </Badge>
                  ))}
                  {PERMISSION_FIELDS.every((field) => !user[field.key]) && (
                    <span className="text-sm text-text-muted">—</span>
                  )}
                </div>
              </Td>
              <Td>
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="secondary" onClick={() => handleEdit(user)}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setResettingId(user.id);
                        setNewPassword("");
                      }}
                    >
                      Reset password
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => handleDelete(user)}>
                      Delete
                    </Button>
                  </div>
                  {resettingId === user.id && (
                    <div className="flex flex-wrap items-center gap-2">
                      <Input
                        type="password"
                        placeholder="New password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        minLength={8}
                      />
                      <Button
                        size="sm"
                        onClick={() => handleConfirmReset(user)}
                        disabled={newPassword.length < 8}
                      >
                        Confirm
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setResettingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </Td>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
