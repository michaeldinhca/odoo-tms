import { useReducer } from "react";
import { DEPOT, FIXTURE_VEHICLES, buildFixtureBoardState } from "../loadPlanning/fixtures";
import { boardReducer } from "../loadPlanning/reducer";
import { UnassignedPanel } from "../loadPlanning/UnassignedPanel";
import { VehicleCard } from "../loadPlanning/VehicleCard";

export default function LoadPlanningPage() {
  const [board] = useReducer(boardReducer, undefined, buildFixtureBoardState);

  return (
    <div className="mx-auto max-w-7xl p-6">
      <h1 className="mb-2 text-2xl font-semibold text-text">Load planning</h1>
      <p className="mb-4 text-sm text-text-muted">
        Static layout preview — drag-and-drop assignment lands in a later phase. Data below is
        fixture/mock data, not a real planning run.
      </p>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="lg:w-96 lg:shrink-0">
          <UnassignedPanel pickings={board.unassigned} depot={DEPOT} />
        </div>

        <div className="grid flex-1 grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {FIXTURE_VEHICLES.map((vehicle) => (
            <VehicleCard key={vehicle.id} vehicle={vehicle} pickings={board.vehicles[vehicle.id] ?? []} />
          ))}
        </div>
      </div>
    </div>
  );
}
