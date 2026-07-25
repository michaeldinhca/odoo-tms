import { useState } from "react";
import { getTenantId, runPlanning } from "../api/client";
import type { Address, PlanningRunResult } from "../api/types";
import { Badge, Button, Card, Table, TableBody, TableHead, TableRow, Td, Th } from "../components/ui";

function formatAddress(address: Address): string {
  const parts = [
    [address.street, address.street2].filter(Boolean).join(", "),
    address.city,
    address.zip,
    address.country_name,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : "—";
}

export default function PlanningPage() {
  const tenantId = getTenantId();
  const [result, setResult] = useState<PlanningRunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!tenantId) return <p className="p-6 text-text">Not logged in.</p>;

  async function handleRun() {
    setError(null);
    setRunning(true);
    setResult(null);
    try {
      const run = await runPlanning(tenantId!);
      setResult(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Planning run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Run planning</h1>
      <p className="mb-4 text-sm text-text-muted">
        Pulls open deliveries from your connected Odoo instance, assigns them to vehicles (FFD,
        capacity-based, no zones), and sequences each vehicle's route FILO (last loaded = first
        delivered).
      </p>
      <Button onClick={handleRun} disabled={running}>
        {running ? "Running..." : "Run Planning"}
      </Button>
      {error && <p className="mt-4 text-sm text-status-full">{error}</p>}

      {result && (
        <div className="mt-6 flex flex-col gap-6">
          <h2 className="text-lg font-semibold text-text">
            Run {result.run_id} — <Badge variant="accent">{result.status}</Badge>
          </h2>

          {result.routes.length === 0 && <p className="text-sm text-text-muted">No routes produced.</p>}

          {result.routes.map((route) => (
            <Card key={route.vehicle_id} className="p-0">
              <div className="border-b border-border px-4 py-3 text-sm font-medium text-text">
                Vehicle {route.vehicle_id} — {route.estimated_distance_km} km,{" "}
                {route.estimated_duration_min} min
              </div>
              <Table>
                <TableHead>
                  <TableRow>
                    <Th>Stop</Th>
                    <Th>Picking ID</Th>
                    <Th>Status</Th>
                    <Th>Customer</Th>
                    <Th>Items</Th>
                    <Th>Address</Th>
                    <Th>Scheduled</Th>
                    <Th>Source Doc</Th>
                    <Th>Warehouse</Th>
                    <Th>ETA</Th>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {route.sequence.map((stop) => (
                    <TableRow key={stop.picking_id}>
                      <Td>{stop.stop_order}</Td>
                      <Td>{stop.picking_id}</Td>
                      <Td>{stop.state || "—"}</Td>
                      <Td>{stop.customer_name || "—"}</Td>
                      <Td>{stop.items_summary || "—"}</Td>
                      <Td>{formatAddress(stop.address)}</Td>
                      <Td className="text-text-muted">{stop.scheduled_date ?? "—"}</Td>
                      <Td>{stop.origin || "—"}</Td>
                      <Td>{stop.warehouse_name || "—"}</Td>
                      <Td className="text-text-muted">{stop.eta ?? "—"}</Td>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          ))}

          {result.unassigned_picking_ids.length > 0 && (
            <Card className="border-status-full/30 bg-status-full/5">
              <p className="text-sm text-status-full">
                Unassigned pickings (no vehicle had capacity):{" "}
                {result.unassigned_picking_ids.join(", ")}
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
