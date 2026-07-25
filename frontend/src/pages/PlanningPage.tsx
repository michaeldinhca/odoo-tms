import { useState } from "react";
import { getTenantId, runPlanning } from "../api/client";
import type { Address, PlanningRunResult } from "../api/types";

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

  if (!tenantId) return <p className="page">Not logged in.</p>;

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
    <div className="page">
      <h1>Run planning</h1>
      <p className="hint">
        Pulls open deliveries from your connected Odoo instance, assigns them to vehicles
        (FFD, capacity-based, no zones), and sequences each vehicle's route FILO (last
        loaded = first delivered).
      </p>
      <button onClick={handleRun} disabled={running}>
        {running ? "Running..." : "Run Planning"}
      </button>
      {error && <p className="error">{error}</p>}

      {result && (
        <div className="results">
          <h2>
            Run {result.run_id} — {result.status}
          </h2>

          {result.routes.length === 0 && <p>No routes produced.</p>}

          {result.routes.map((route) => (
            <table key={route.vehicle_id} className="route-table">
              <caption>
                Vehicle {route.vehicle_id} — {route.estimated_distance_km} km,{" "}
                {route.estimated_duration_min} min
              </caption>
              <thead>
                <tr>
                  <th>Stop</th>
                  <th>Picking ID</th>
                  <th>Status</th>
                  <th>Customer</th>
                  <th>Items</th>
                  <th>Address</th>
                  <th>Scheduled</th>
                  <th>Source Doc</th>
                  <th>Warehouse</th>
                  <th>ETA</th>
                </tr>
              </thead>
              <tbody>
                {route.sequence.map((stop) => (
                  <tr key={stop.picking_id}>
                    <td>{stop.stop_order}</td>
                    <td>{stop.picking_id}</td>
                    <td>{stop.state || "—"}</td>
                    <td>{stop.customer_name || "—"}</td>
                    <td>{stop.items_summary || "—"}</td>
                    <td>{formatAddress(stop.address)}</td>
                    <td>{stop.scheduled_date ?? "—"}</td>
                    <td>{stop.origin || "—"}</td>
                    <td>{stop.warehouse_name || "—"}</td>
                    <td>{stop.eta ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}

          {result.unassigned_picking_ids.length > 0 && (
            <p className="error">
              Unassigned pickings (no vehicle had capacity):{" "}
              {result.unassigned_picking_ids.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
