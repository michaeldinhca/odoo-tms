import type { BoardAction, BoardState } from "./types";

export function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case "SELECT_ITEM":
      // Stubbed — multi-select interaction lands in the drag-and-drop phase.
      // Deliberately not touching `selectedIds` yet so this phase stays
      // read-only, per the task's own scope boundary.
      return state;
    default:
      return state;
  }
}
