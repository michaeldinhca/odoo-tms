import { useDraggable, useDroppable } from "@dnd-kit/core";
import { useMemo, useState } from "react";
import { Card, cn } from "../components/ui";
import { clusterDestinations, type Coordinates, type CompassDirection } from "../lib/clustering";
import { UNASSIGNED_CONTAINER_ID, type Picking } from "./types";

const DIRECTION_LABELS: Record<CompassDirection, string> = {
  N: "North",
  NE: "Northeast",
  E: "East",
  SE: "Southeast",
  S: "South",
  SW: "Southwest",
  W: "West",
  NW: "Northwest",
};

function formatDistanceRange(minKm: number, maxKm: number): string {
  const min = Math.round(minKm);
  const max = Math.round(maxKm);
  return min === max ? `${min}km` : `${min}-${max}km`;
}

function PickingRow({ picking }: { picking: Picking }) {
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: picking.id,
    data: { containerId: UNASSIGNED_CONTAINER_ID },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        "flex cursor-grab items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2",
        "touch-none transition-colors hover:bg-bg active:cursor-grabbing motion-reduce:transition-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        isDragging && "opacity-40",
      )}
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-text">{picking.customerName}</p>
        <p className="truncate text-xs text-text-muted">{picking.address}</p>
      </div>
      <div className="shrink-0 text-right text-xs text-text-muted">
        <p>
          {picking.weightKg}kg · {picking.volumeM3}m³
        </p>
        <p>{Math.round(picking.distanceFromDepotKm)}km</p>
      </div>
    </div>
  );
}

interface UnassignedPanelProps {
  pickings: Picking[];
  depot: Coordinates;
}

export function UnassignedPanel({ pickings, depot }: UnassignedPanelProps) {
  const clusters = useMemo(() => clusterDestinations(pickings, depot), [pickings, depot]);
  const [collapsed, setCollapsed] = useState<Set<CompassDirection>>(new Set());
  const { setNodeRef, isOver } = useDroppable({ id: UNASSIGNED_CONTAINER_ID });

  function toggle(direction: CompassDirection) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(direction)) next.delete(direction);
      else next.add(direction);
      return next;
    });
  }

  return (
    <Card
      ref={setNodeRef}
      heading={`Unassigned (${pickings.length})`}
      className={cn("flex flex-col gap-3", isOver && "ring-2 ring-accent")}
    >
      {pickings.length === 0 ? (
        <p className="text-sm text-text-muted">
          No unassigned pickings — everything has been assigned to a vehicle.
        </p>
      ) : (
        clusters.map((cluster) => {
          const isCollapsed = collapsed.has(cluster.direction);
          return (
            <div key={cluster.direction} className="rounded-md border border-border">
              <button
                type="button"
                onClick={() => toggle(cluster.direction)}
                aria-expanded={!isCollapsed}
                className="flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left transition-colors hover:bg-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent motion-reduce:transition-none"
              >
                <span className="text-sm font-medium text-text">
                  {DIRECTION_LABELS[cluster.direction]}{" "}
                  <span className="font-normal text-text-muted">
                    ({cluster.items.length} order{cluster.items.length === 1 ? "" : "s"},{" "}
                    {formatDistanceRange(cluster.minDistanceKm, cluster.maxDistanceKm)})
                  </span>
                </span>
                <svg
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  aria-hidden="true"
                  className={cn(
                    "shrink-0 text-text-muted transition-transform motion-reduce:transition-none",
                    isCollapsed ? "-rotate-90" : "rotate-0",
                  )}
                >
                  <path fill="currentColor" d="M7 10l5 5 5-5z" />
                </svg>
              </button>
              {!isCollapsed && (
                <div className="flex flex-col gap-2 border-t border-border p-2">
                  {cluster.items.map((picking) => (
                    <PickingRow key={picking.id} picking={picking} />
                  ))}
                </div>
              )}
            </div>
          );
        })
      )}
    </Card>
  );
}
