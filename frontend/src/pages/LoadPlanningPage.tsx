import {
  closestCenter,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useReducer, useState } from "react";
import { DEPOT, FIXTURE_VEHICLES, buildFixtureBoardState } from "../loadPlanning/fixtures";
import { boardReducer, findPickingById } from "../loadPlanning/reducer";
import type { Picking } from "../loadPlanning/types";
import { UnassignedPanel } from "../loadPlanning/UnassignedPanel";
import { VehicleCard } from "../loadPlanning/VehicleCard";

/** Lightweight floating preview shown under the cursor/touch point while
 * dragging — the original card stays in place (dimmed), this is the copy
 * that actually follows the pointer (see DragOverlay below). */
function DragPreviewCard({ picking }: { picking: Picking }) {
  return (
    <div className="cursor-grabbing rounded-md border border-accent bg-surface px-3 py-2 shadow-sm">
      <p className="text-sm font-medium text-text">{picking.customerName}</p>
      <p className="text-xs text-text-muted">
        {picking.weightKg}kg · {picking.volumeM3}m³
      </p>
    </div>
  );
}

export default function LoadPlanningPage() {
  const [board, dispatch] = useReducer(boardReducer, undefined, buildFixtureBoardState);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor),
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return; // dropped outside any droppable — leave the board untouched

    const sourceContainerId = active.data.current?.containerId as string | undefined;
    const destinationContainerId = String(over.id);
    if (!sourceContainerId || sourceContainerId === destinationContainerId) return;

    dispatch({ type: "MOVE_ITEMS", pickingIds: [String(active.id)], destinationContainerId });
  }

  const activePicking = activeId ? findPickingById(board, activeId) : undefined;

  return (
    <div className="mx-auto max-w-7xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Load planning</h1>
      <p className="mb-4 text-sm text-text-muted">
        Drag a picking from the unassigned list onto a vehicle, or between vehicles. Fixture/mock
        data, not a real planning run — nothing here is saved yet.
      </p>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <div className="lg:w-96 lg:shrink-0">
            <UnassignedPanel pickings={board.unassigned} depot={DEPOT} />
          </div>

          <div className="grid flex-1 grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {FIXTURE_VEHICLES.map((vehicle) => (
              <VehicleCard
                key={vehicle.id}
                vehicle={vehicle}
                pickings={board.vehicles[vehicle.id] ?? []}
              />
            ))}
          </div>
        </div>

        <DragOverlay>{activePicking ? <DragPreviewCard picking={activePicking} /> : null}</DragOverlay>
      </DndContext>
    </div>
  );
}
