/** Geo distance/bearing helpers and compass-direction clustering.
 *
 * `getDistanceKm` ports `haversine_distance_km` from
 * `backend/app/services/planning/haversine.py` (same formula, same Earth
 * radius constant) so on-screen distances read consistently with what the
 * backend computes for actual route planning. Bearing/compass-direction
 * grouping has no backend equivalent — it's purely a frontend concern for
 * the load-planning board's unassigned-pickings panel.
 */

const EARTH_RADIUS_KM = 6371.0088;

export interface Coordinates {
  lat: number;
  lng: number;
}

export type CompassDirection = "N" | "NE" | "E" | "SE" | "S" | "SW" | "W" | "NW";

const COMPASS_DIRECTIONS: CompassDirection[] = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

function toRadians(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

/** Great-circle distance between two points, in kilometers. */
export function getDistanceKm(from: Coordinates, to: Coordinates): number {
  const dLat = toRadians(to.lat - from.lat);
  const dLng = toRadians(to.lng - from.lng);
  const phi1 = toRadians(from.lat);
  const phi2 = toRadians(to.lat);

  const a = Math.sin(dLat / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLng / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_KM * c;
}

/** Initial compass bearing from `from` to `to`, in degrees [0, 360). */
export function getBearing(from: Coordinates, to: Coordinates): number {
  const phi1 = toRadians(from.lat);
  const phi2 = toRadians(to.lat);
  const dLng = toRadians(to.lng - from.lng);

  const y = Math.sin(dLng) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLng);
  const theta = Math.atan2(y, x);
  return ((theta * 180) / Math.PI + 360) % 360;
}

/** Buckets a bearing into one of 8 compass directions (45° sectors,
 * centered on N/NE/E/.../NW). */
export function getCompassDirection(bearingDegrees: number): CompassDirection {
  const normalized = ((bearingDegrees % 360) + 360) % 360;
  const index = Math.round(normalized / 45) % 8;
  return COMPASS_DIRECTIONS[index];
}

export interface DirectionCluster<T> {
  direction: CompassDirection;
  items: T[];
  minDistanceKm: number;
  maxDistanceKm: number;
}

/** Groups `items` by compass direction from `origin`, sorting each group's
 * items by distance ascending. Returned clusters are ordered clockwise
 * from N; directions with no items are omitted rather than returned empty. */
export function clusterDestinations<T extends Coordinates>(
  items: T[],
  origin: Coordinates,
): DirectionCluster<T>[] {
  const groups = new Map<CompassDirection, T[]>();

  for (const item of items) {
    const direction = getCompassDirection(getBearing(origin, item));
    const group = groups.get(direction);
    if (group) group.push(item);
    else groups.set(direction, [item]);
  }

  return COMPASS_DIRECTIONS.filter((direction) => groups.has(direction)).map((direction) => {
    const withDistance = groups
      .get(direction)!
      .map((item) => ({ item, distanceKm: getDistanceKm(origin, item) }))
      .sort((a, b) => a.distanceKm - b.distanceKm);

    return {
      direction,
      items: withDistance.map((w) => w.item),
      minDistanceKm: withDistance[0].distanceKm,
      maxDistanceKm: withDistance[withDistance.length - 1].distanceKm,
    };
  });
}
