import { useDraggable, useDroppable } from "@dnd-kit/core";
import { CapacityBar, Card, cn } from "../components/ui";
import type { Picking, Vehicle } from "./types";

interface StopRowProps {
  stopNumber: number;
  picking: Picking;
  vehicleId: string;
}

function StopRow({ stopNumber, picking, vehicleId }: StopRowProps) {
  const { setNodeRef, listeners, attributes, isDragging } = useDraggable({
    id: picking.id,
    data: { containerId: vehicleId },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        "flex cursor-grab items-center gap-3 rounded-md border border-border bg-surface px-3 py-2",
        "touch-none transition-colors hover:bg-bg active:cursor-grabbing motion-reduce:transition-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        isDragging && "opacity-40",
      )}
    >
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
}

export function VehicleCard({ vehicle, pickings }: VehicleCardProps) {
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
            <StopRow key={picking.id} stopNumber={index + 1} picking={picking} vehicleId={vehicle.id} />
          ))}
        </div>
      )}
    </Card>
  );
}
