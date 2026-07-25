import { UNASSIGNED_CONTAINER_ID, type BoardAction, type BoardState, type Picking } from "./types";

function getContainerItems(state: BoardState, containerId: string): Picking[] {
  return containerId === UNASSIGNED_CONTAINER_ID
    ? state.unassigned
    : (state.vehicles[containerId] ?? []);
}

/** Every picking currently on the board, regardless of container — used
 * both by the reducer (to resolve where a moved id currently lives) and
 * by the page to look up the picking being dragged for the DragOverlay. */
export function findPickingById(state: BoardState, pickingId: string): Picking | undefined {
  const inUnassigned = state.unassigned.find((p) => p.id === pickingId);
  if (inUnassigned) return inUnassigned;
  for (const items of Object.values(state.vehicles)) {
    const found = items.find((p) => p.id === pickingId);
    if (found) return found;
  }
  return undefined;
}

function moveItems(
  state: BoardState,
  pickingIds: string[],
  destinationContainerId: string,
): BoardState {
  const idSet = new Set(pickingIds);
  if (idSet.size === 0) return state;

  // No-op guard: every id being "moved" is already sitting in the
  // destination container — e.g. dropping a card back where it came
  // from. Returning the exact same state reference lets useReducer bail
  // out of re-rendering entirely, per the task's "no visual flicker"
  // requirement — this isn't just an early return for its own sake.
  const destinationIds = new Set(getContainerItems(state, destinationContainerId).map((p) => p.id));
  if (pickingIds.every((id) => destinationIds.has(id))) return state;

  const movedPickings = pickingIds
    .map((id) => findPickingById(state, id))
    .filter((p): p is Picking => p != null);
  if (movedPickings.length === 0) return state;

  const nextUnassigned = state.unassigned.filter((p) => !idSet.has(p.id));
  const nextVehicles: Record<string, Picking[]> = {};
  for (const [vehicleId, items] of Object.entries(state.vehicles)) {
    nextVehicles[vehicleId] = items.filter((p) => !idSet.has(p.id));
  }

  // Appended to the end of the destination — the "first loaded" position.
  // Re-sequencing within a vehicle is a manual reordering feature for a
  // later phase, not inferred here (see the task's own scope boundary).
  if (destinationContainerId === UNASSIGNED_CONTAINER_ID) {
    nextUnassigned.push(...movedPickings);
  } else {
    nextVehicles[destinationContainerId] = [
      ...(nextVehicles[destinationContainerId] ?? []),
      ...movedPickings,
    ];
  }

  return { ...state, unassigned: nextUnassigned, vehicles: nextVehicles };
}

export function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case "SELECT_ITEM":
      // Stubbed — multi-select interaction lands in a later phase.
      return state;
    case "MOVE_ITEMS":
      return moveItems(state, action.pickingIds, action.destinationContainerId);
    default:
      return state;
  }
}
