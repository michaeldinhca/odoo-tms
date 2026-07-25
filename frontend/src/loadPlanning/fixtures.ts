import { getDistanceKm } from "../lib/clustering";
import type { BoardState, Picking, Vehicle } from "./types";

/** Fixed depot coordinate all fixture distances/bearings are measured
 * from — roughly downtown Toronto, matching the "1 Depot Rd" flavor used
 * in existing backend test fixtures (see backend/tests/test_sync_config.py). */
export const DEPOT = { lat: 43.6532, lng: -79.3832 };

type PickingSeed = Omit<Picking, "distanceFromDepotKm">;

const PICKING_SEEDS: PickingSeed[] = [
  {
    id: "scarborough-riverside",
    customerName: "Riverside Fabrication",
    address: "120 Ellesmere Rd, Scarborough, ON",
    lat: 43.7764,
    lng: -79.2318,
    weightKg: 180,
    volumeM3: 1.2,
  },
  {
    id: "north-york-dental",
    customerName: "North York Dental Supply",
    address: "45 Sheppard Ave E, North York, ON",
    lat: 43.7615,
    lng: -79.4111,
    weightKg: 45,
    volumeM3: 0.3,
  },
  {
    id: "etobicoke-hardware",
    customerName: "Etobicoke Hardware Co.",
    address: "800 Kipling Ave, Etobicoke, ON",
    lat: 43.6205,
    lng: -79.5132,
    weightKg: 220,
    volumeM3: 1.8,
  },
  {
    id: "leslieville-coffee",
    customerName: "Leslieville Coffee Roasters",
    address: "1050 Queen St E, Toronto, ON",
    lat: 43.6629,
    lng: -79.3389,
    weightKg: 60,
    volumeM3: 0.5,
  },
  {
    id: "mississauga-auto",
    customerName: "Mississauga Auto Parts",
    address: "300 Dundas St W, Mississauga, ON",
    lat: 43.589,
    lng: -79.6441,
    weightKg: 310,
    volumeM3: 2.4,
  },
  {
    id: "beaches-home-goods",
    customerName: "Beaches Home Goods",
    address: "1900 Queen St E, Toronto, ON",
    lat: 43.6708,
    lng: -79.2952,
    weightKg: 90,
    volumeM3: 0.7,
  },
  {
    id: "vaughan-textiles",
    customerName: "Vaughan Textiles",
    address: "60 Bass Pro Mills Dr, Vaughan, ON",
    lat: 43.8361,
    lng: -79.4983,
    weightKg: 150,
    volumeM3: 1.1,
  },
  {
    id: "downtown-print",
    customerName: "Downtown Print Shop",
    address: "200 Bay St, Toronto, ON",
    lat: 43.6489,
    lng: -79.3817,
    weightKg: 25,
    volumeM3: 0.15,
  },
  {
    id: "markham-electronics",
    customerName: "Markham Electronics",
    address: "3235 Hwy 7, Markham, ON",
    lat: 43.8561,
    lng: -79.337,
    weightKg: 130,
    volumeM3: 0.9,
  },
  {
    id: "junction-furniture",
    customerName: "Junction Furniture",
    address: "2960 Dundas St W, Toronto, ON",
    lat: 43.6636,
    lng: -79.4634,
    weightKg: 275,
    volumeM3: 2.1,
  },
];

/** Every fixture picking, keyed by id, with `distanceFromDepotKm` computed
 * once from the seed coordinates — this is the "pool" the board's initial
 * state is assembled from below. */
export const FIXTURE_PICKINGS: Record<string, Picking> = Object.fromEntries(
  PICKING_SEEDS.map((seed) => [
    seed.id,
    { ...seed, distanceFromDepotKm: getDistanceKm(DEPOT, seed) },
  ]),
);

export const FIXTURE_VEHICLES: Vehicle[] = [
  { id: "van-1", name: "Van 1", capacityKg: 500, capacityM3: 4 },
  { id: "truck-1", name: "Truck 1", capacityKg: 900, capacityM3: 8 },
  { id: "van-2", name: "Van 2", capacityKg: 800, capacityM3: 6 },
];

/** Picking ids per vehicle, in FILO delivery order (index 0 = first
 * delivered = last loaded). Deliberately spans a few different
 * `CapacityBar` states: `van-1` sits at 99%/97.5% (weight/volume) to show
 * the "warning" band, `truck-1` is comfortably under capacity ("ok"), and
 * `van-2` is left with no assignments to exercise the empty vehicle-card
 * state. */
const FIXTURE_ASSIGNMENTS: Record<string, string[]> = {
  "van-1": ["junction-furniture", "etobicoke-hardware"],
  "truck-1": ["downtown-print", "leslieville-coffee", "mississauga-auto"],
  "van-2": [],
};

/** Builds the board's initial state from the fixtures above. This is the
 * one function a later phase swaps out for a real API call — everything
 * downstream (the reducer, the panels) only depends on `BoardState`. */
export function buildFixtureBoardState(): BoardState {
  const assignedIds = new Set(Object.values(FIXTURE_ASSIGNMENTS).flat());

  const vehicles: Record<string, Picking[]> = {};
  for (const [vehicleId, pickingIds] of Object.entries(FIXTURE_ASSIGNMENTS)) {
    vehicles[vehicleId] = pickingIds.map((id) => FIXTURE_PICKINGS[id]);
  }

  const unassigned = Object.values(FIXTURE_PICKINGS).filter((p) => !assignedIds.has(p.id));

  return { unassigned, vehicles, selectedIds: new Set() };
}
