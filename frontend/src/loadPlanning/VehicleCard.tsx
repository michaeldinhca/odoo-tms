import { useDraggable, useDroppable } from "@dnd-kit/core";
import type { MouseEvent } from "react";
import { CapacityBar, Card, cn } from "../components/ui";
import type { BoardAction, Picking, Vehicle } from "./types";

interface StopRowProps {
  stopNumber: number;
  picking: Picking;
  vehicleId: string;
  isSelected: boolean;
  dispatch: React.Dispatch<BoardAction>;
}

function StopRow({ stopNumber, picking, vehicleId, isSelected, dispatch }: StopRowProps) {
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: picking.id,
    data: { containerId: vehicleId },
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
        "flex cursor-grab items-center gap-3 rounded-md border px-3 py-2",
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
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-bg text-xs font-medium text-text-muted">
        {stopNumber}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text">{picking.customerName}</p>
        <p className="truncate text-xs text-text-muted">{picking.address}</p>
      </div>
      <div className="shrink-0 text-right text-xs text-text-muted">
        {picking.weightKg}kg · {picking.volumeM3}m³
      </div>
    </div>
  );
}

interface VehicleCardProps {
  vehicle: Vehicle;
  pickings: Picking[];
  selectedIds: Set<string>;
  dispatch: React.Dispatch<BoardAction>;
}

export function VehicleCard({ vehicle, pickings, selectedIds, dispatch }: VehicleCardProps) {
  const { setNodeRef, isOver } = useDroppable({ id: vehicle.id });
  const totalWeightKg = pickings.reduce((sum, p) => sum + p.weightKg, 0);
  const totalVolumeM3 = pickings.reduce((sum, p) => sum + p.volumeM3, 0);

  return (
    <Card
      ref={setNodeRef}
      heading={vehicle.name}
      className={cn("flex flex-col gap-4", isOver && "ring-2 ring-accent")}
    >
      <div className="flex flex-col gap-2">
        <CapacityBar label="Weight" value={totalWeightKg} max={vehicle.capacityKg} />
        <CapacityBar label="Volume" value={totalVolumeM3} max={vehicle.capacityM3} />
      </div>

      {pickings.length === 0 ? (
        <p className="text-sm text-text-muted">No pickings assigned yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            Stops — FILO (last loaded, first delivered)
          </p>
          {pickings.map((picking, index) => (
            <StopRow
              key={picking.id}
              stopNumber={index + 1}
              picking={picking}
              vehicleId={vehicle.id}
              isSelected={selectedIds.has(picking.id)}
              dispatch={dispatch}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
