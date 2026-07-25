import { useDraggable, useDroppable } from "@dnd-kit/core";
import { type MouseEvent, useMemo, useState } from "react";
import { Card, cn } from "../components/ui";
import { clusterDestinations, type Coordinates, type CompassDirection } from "../lib/clustering";
import { UNASSIGNED_CONTAINER_ID, type BoardAction, type Picking } from "./types";

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

/** Six-dot grip glyph — the drag affordance for a cluster header, kept
 * visually distinct from an individual card (which is draggable across
 * its whole row, cursor-grab only, no explicit handle). */
function GripIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <circle cx="9" cy="6" r="1.5" fill="currentColor" />
      <circle cx="9" cy="12" r="1.5" fill="currentColor" />
      <circle cx="9" cy="18" r="1.5" fill="currentColor" />
      <circle cx="15" cy="6" r="1.5" fill="currentColor" />
      <circle cx="15" cy="12" r="1.5" fill="currentColor" />
      <circle cx="15" cy="18" r="1.5" fill="currentColor" />
    </svg>
  );
}

interface PickingRowProps {
  picking: Picking;
  isSelected: boolean;
  dispatch: React.Dispatch<BoardAction>;
}

function PickingRow({ picking, isSelected, dispatch }: PickingRowProps) {
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: picking.id,
    data: { containerId: UNASSIGNED_CONTAINER_ID },
  });

  function handleClick(event: MouseEvent) {
    const mode = event.metaKey || event.ctrlKey ? "toggle" : "replace";
    dispatch({ type: "SELECT_ITEM", pickingId: picking.id, mode });
  }

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={handleClick}
      className={cn(
        "flex cursor-grab items-center justify-between gap-3 rounded-md border px-3 py-2",
        "touch-none transition-colors active:cursor-grabbing motion-reduce:transition-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        isSelected ? "border-accent bg-accent/5" : "border-border bg-surface hover:bg-bg",
        isDragging && "opacity-40",
      )}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={() => dispatch({ type: "SELECT_ITEM", pickingId: picking.id, mode: "toggle" })}
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        aria-label={`Select ${picking.customerName}`}
        className="h-4 w-4 shrink-0 accent-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      />
      <div className="min-w-0 flex-1">
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

interface ClusterDragHandleProps {
  direction: CompassDirection;
  pickingIds: string[];
}

function ClusterDragHandle({ direction, pickingIds }: ClusterDragHandleProps) {
  // Carries the full picking-id list from the clustered *data*
  // (`clusterDestinations` output), not anything read off the DOM — so a
  // collapsed cluster still drags every item it contains.
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: `cluster-${direction}`,
    data: { containerId: UNASSIGNED_CONTAINER_ID, pickingIds },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      role="button"
      tabIndex={0}
      aria-label={`Drag all ${pickingIds.length} pickings in ${DIRECTION_LABELS[direction]}`}
      className={cn(
        "flex shrink-0 cursor-grab touch-none items-center justify-center rounded-md p-2 text-text-muted",
        "transition-colors hover:bg-bg hover:text-text active:cursor-grabbing motion-reduce:transition-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        isDragging && "opacity-40",
      )}
    >
      <GripIcon />
    </div>
  );
}

interface UnassignedPanelProps {
  pickings: Picking[];
  depot: Coordinates;
  selectedIds: Set<string>;
  dispatch: React.Dispatch<BoardAction>;
}

export function UnassignedPanel({ pickings, depot, selectedIds, dispatch }: UnassignedPanelProps) {
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
              <div className="flex items-center gap-1 p-1">
                <ClusterDragHandle
                  direction={cluster.direction}
                  pickingIds={cluster.items.map((p) => p.id)}
                />
                <button
                  type="button"
                  onClick={() => toggle(cluster.direction)}
                  aria-expanded={!isCollapsed}
                  className="flex flex-1 items-center justify-between gap-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent motion-reduce:transition-none"
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
              </div>
              {!isCollapsed && (
                <div className="flex flex-col gap-2 border-t border-border p-2">
                  {cluster.items.map((picking) => (
                    <PickingRow
                      key={picking.id}
                      picking={picking}
                      isSelected={selectedIds.has(picking.id)}
                      dispatch={dispatch}
                    />
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
