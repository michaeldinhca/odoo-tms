/** A single delivery to be assigned to a vehicle. Local board-domain type,
 * not a wire type — the real API's `RouteStop`/`stock.picking` data has no
 * lat/lng or weight/volume yet (see SPEC.md), so this shape is what a
 * future integration phase will need to map *into*, not something that
 * exists on the backend today. */
export interface Picking {
  id: string;
  customerName: string;
  address: string;
  lat: number;
  lng: number;
  weightKg: number;
  volumeM3: number;
  /** Great-circle distance from the depot, in km — computed once via
   * `getDistanceKm` when the picking is loaded, not derived at render time. */
  distanceFromDepotKm: number;
}

export interface Vehicle {
  id: string;
  name: string;
  capacityKg: number;
  capacityM3: number;
}

export interface BoardState {
  unassigned: Picking[];
  /** Assignments only — vehicle metadata (name/capacity) lives in a
   * separate `Vehicle[]` roster, not in board state. Array order is the
   * FILO delivery sequence: index 0 = first delivered = last loaded (see
   * `backend/app/services/planning/filo.py::sequence_filo` — this mirrors
   * the same convention the backend already uses for `RouteStop.stop_order`). */
  vehicles: Record<string, Picking[]>;
  /** Picking ids currently selected — wired up for the drag/multi-select
   * phase; nothing reads or sets this yet beyond the stubbed reducer case. */
  selectedIds: Set<string>;
}

/** Well-known droppable/container id for the unassigned panel — vehicle
 * ids are the container ids everywhere else, so this needs its own
 * sentinel that can't collide with a real vehicle id. */
export const UNASSIGNED_CONTAINER_ID = "unassigned";

export type BoardAction =
  | { type: "SELECT_ITEM"; pickingId: string }
  | {
      type: "MOVE_ITEMS";
      /** Always a single-element array in the drag-and-drop phase — kept
       * as an array so a later multi-select phase can move several
       * pickings in one dispatch without a new action type. */
      pickingIds: string[];
      destinationContainerId: string;
    };
