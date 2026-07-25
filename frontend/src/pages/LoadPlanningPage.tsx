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
import { Badge } from "../components/ui";
import { DEPOT, FIXTURE_VEHICLES, buildFixtureBoardState } from "../loadPlanning/fixtures";
import { boardReducer, findPickingById } from "../loadPlanning/reducer";
import type { Picking } from "../loadPlanning/types";
import { UnassignedPanel } from "../loadPlanning/UnassignedPanel";
import { VehicleCard } from "../loadPlanning/VehicleCard";

/** Lightweight floating preview for a single-picking drag — shown under
 * the cursor/touch point (see DragOverlay below) while the original card
 * stays in place, dimmed. */
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

/** Floating preview for a cluster-header or multi-select drag — a count
 * badge instead of a single card, since there's no one picking to show. */
function MultiDragPreview({ count }: { count: number }) {
  return (
    <div className="flex cursor-grabbing items-center gap-2 rounded-md border border-accent bg-surface px-3 py-2 shadow-sm">
      <Badge variant="accent">{count} items</Badge>
      <span className="text-sm text-text-muted">Moving together</span>
    </div>
  );
}

interface ActiveDrag {
  pickingIds: string[];
}

export default function LoadPlanningPage() {
  const [board, dispatch] = useReducer(boardReducer, undefined, buildFixtureBoardState);
  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor),
  );

  function handleDragStart(event: DragStartEvent) {
    const draggedId = String(event.active.id);
    // A cluster header carries its full membership directly in `data` —
    // computed from the clustered data, not the rendered DOM, so a
    // collapsed cluster still resolves every item (see
    // UnassignedPanel's ClusterDragHandle). Otherwise, dragging a card
    // that's part of the current selection carries the whole selection;
    // dragging an unselected card carries just itself, even if some
    // stale selection exists elsewhere.
    const clusterPickingIds = event.active.data.current?.pickingIds as string[] | undefined;
    const pickingIds =
      clusterPickingIds ??
      (board.selectedIds.has(draggedId) ? Array.from(board.selectedIds) : [draggedId]);
    setActiveDrag({ pickingIds });
  }

  function handleDragEnd(event: DragEndEvent) {
    const { over } = event;
    const pickingIds = activeDrag?.pickingIds ?? [];
    setActiveDrag(null);
    if (!over || pickingIds.length === 0) return;

    // No same-container short-circuit here: a multi-select can span
    // several source containers at once, so "is this a no-op" isn't a
    // single comparison the way it is for one card. The reducer's own
    // membership check (see moveItems) already covers every case
    // correctly and returns the identical state reference when nothing
    // actually needs to move.
    dispatch({ type: "MOVE_ITEMS", pickingIds, destinationContainerId: String(over.id) });
  }

  const activePicking =
    activeDrag && activeDrag.pickingIds.length === 1
      ? findPickingById(board, activeDrag.pickingIds[0])
      : undefined;

  return (
    <div className="mx-auto max-w-7xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Load planning</h1>
      <p className="mb-4 text-sm text-text-muted">
        Drag a picking, a whole compass cluster, or a multi-selection (checkbox, or click and
        ctrl/cmd-click) onto a vehicle or back to unassigned. Fixture/mock data — nothing here is
        saved yet.
      </p>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <div className="lg:w-96 lg:shrink-0">
            <UnassignedPanel
              pickings={board.unassigned}
              depot={DEPOT}
              selectedIds={board.selectedIds}
              dispatch={dispatch}
            />
          </div>

          <div className="grid flex-1 grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {FIXTURE_VEHICLES.map((vehicle) => (
              <VehicleCard
                key={vehicle.id}
                vehicle={vehicle}
                pickings={board.vehicles[vehicle.id] ?? []}
                selectedIds={board.selectedIds}
                dispatch={dispatch}
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeDrag && activeDrag.pickingIds.length > 1 ? (
            <MultiDragPreview count={activeDrag.pickingIds.length} />
          ) : activePicking ? (
            <DragPreviewCard picking={activePicking} />
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
