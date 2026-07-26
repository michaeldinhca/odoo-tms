import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Fragment } from "react";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";
import type { WarehouseRoute, WarehouseRouteStop } from "../api/types";

interface RouteMapProps {
  warehouse: { name: string; lat: number; lng: number };
  routes: WarehouseRoute[];
}

/** A stop auto-created from a stock.picking address (see DECISIONS.md)
 * may have no coordinates yet — it just can't be placed on the map until
 * an admin fills them in, same as it can't have a distance computed. */
function stopPosition(stop: WarehouseRouteStop): [number, number] | null {
  const { lat, lng } = stop.destination;
  return lat != null && lng != null ? [lat, lng] : null;
}

/** Small inline-HTML/CSS circle markers via L.divIcon, not Leaflet's
 * default image-based L.Icon — sidesteps the well-known bundler/Vite
 * asset-path breakage with Leaflet's default marker images, and makes
 * per-route coloring trivial without needing a colored PNG per palette
 * color. */
const WAREHOUSE_ICON = L.divIcon({
  className: "",
  html:
    '<div style="width:16px;height:16px;background:#0F172A;border:2px solid white;' +
    'border-radius:3px;box-shadow:0 0 0 1px #0F172A;"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

function stopIcon(color: string, stopNumber: number): L.DivIcon {
  return L.divIcon({
    className: "",
    html:
      `<div style="width:20px;height:20px;background:${color};border:2px solid white;` +
      "border-radius:50%;box-shadow:0 0 0 1px rgba(0,0,0,0.3);display:flex;" +
      'align-items:center;justify-content:center;color:white;font-size:11px;' +
      `font-weight:600;font-family:sans-serif;">${stopNumber}</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

/** Renders every route for one warehouse at once, each in its own color —
 * a marker per stop (numbered by stop_order) connected by a straight
 * Polyline from the warehouse through each stop in order. Straight lines
 * only, not real road routing — this project deliberately has no paid
 * routing/matrix API (see DECISIONS.md), same reasoning as the
 * Haversine-only distance calculation. Callers should pass a `key` tied
 * to the selected warehouse when swapping warehouses — react-leaflet's
 * `MapContainer` only reads `center`/`zoom` on initial mount, so changing
 * warehouses requires a remount, not a prop update, to actually recenter. */
export function RouteMap({ warehouse, routes }: RouteMapProps) {
  const center: [number, number] = [warehouse.lat, warehouse.lng];

  return (
    <div className="h-96 w-full overflow-hidden rounded-md border border-border">
      <MapContainer center={center} zoom={11} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={center} icon={WAREHOUSE_ICON}>
          <Popup>{warehouse.name}</Popup>
        </Marker>
        {routes.map((route) => {
          const stopPositions = route.stops
            .map(stopPosition)
            .filter((pos): pos is [number, number] => pos !== null);
          const linePositions: [number, number][] = [center, ...stopPositions];

          return (
            <Fragment key={route.id}>
              {stopPositions.length > 0 && (
                <Polyline positions={linePositions} pathOptions={{ color: route.color, weight: 3 }} />
              )}
              {route.stops.map((stop, index) => {
                const position = stopPosition(stop);
                if (!position) return null;
                return (
                  <Marker key={stop.id} position={position} icon={stopIcon(route.color, index + 1)}>
                    <Popup>
                      <strong>{route.name}</strong> — stop {index + 1}
                      <br />
                      {stop.destination.name}
                      {stop.distance_km != null && (
                        <>
                          <br />
                          {stop.distance_km.toFixed(1)} km from warehouse
                        </>
                      )}
                    </Popup>
                  </Marker>
                );
              })}
            </Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
}
