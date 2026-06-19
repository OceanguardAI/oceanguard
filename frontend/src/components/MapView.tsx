import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polygon, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { RiskEvent } from "../types";
import { fetchMPA } from "../lib/api";
import { getRiskColor } from "../lib/riskColor";

const MapController = ({ selected }: { selected: RiskEvent | null }) => {
  const map = useMap();
  useEffect(() => {
    if (selected) map.setView([selected.lat, selected.lon], 11, { animate: true });
  }, [selected, map]);
  return null;
};

// In scan mode, a click anywhere on the water reports its lat/lon so the officer
// can run a YOLO radar scan at that exact point — any MPA, any area, not just an
// existing detection.
const ScanClickHandler = ({
  active, onPick,
}: { active: boolean; onPick: (lat: number, lon: number) => void }) => {
  useMapEvents({
    click: (e) => { if (active) onPick(e.latlng.lat, e.latlng.lng); },
  });
  return null;
};

// A pulsing cyan crosshair marking the point being scanned.
const scanIcon = L.divIcon({
  className: "",
  html: `
    <div style="position:relative; width:26px; height:26px;">
      <div style="position:absolute; inset:0; border:2px solid #22d3ee; border-radius:50%;
        box-shadow:0 0 10px #22d3ee; animation:oceanScanPulse 1.4s ease-out infinite;"></div>
      <div style="position:absolute; top:50%; left:50%; width:5px; height:5px; transform:translate(-50%,-50%);
        background:#22d3ee; border-radius:50%;"></div>
    </div>
    <style>@keyframes oceanScanPulse{0%{transform:scale(0.6);opacity:1}100%{transform:scale(1.3);opacity:0.2}}</style>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

// Auto-fit the map to show all loaded events on first load.
const FitBounds = ({ events }: { events: RiskEvent[] }) => {
  const map = useMap();
  useEffect(() => {
    if (events.length === 0) return;
    const lats = events.map((e) => e.lat);
    const lons = events.map((e) => e.lon);
    const bounds = L.latLngBounds(
      [Math.min(...lats) - 0.3, Math.min(...lons) - 0.3],
      [Math.max(...lats) + 0.3, Math.max(...lons) + 0.3],
    );
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 10, animate: false });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]); // run once when map is ready; events are stable after initial load
  return null;
};

const RISK_COLORS: Record<string, string> = {
  LOW:      "#22c55e",
  MEDIUM:   "#fbbf24",
  HIGH:     "#f97316",
  CRITICAL: "#dc2626",
};

const createDotIcon = (level: string, isSelected: boolean) => {
  const color  = RISK_COLORS[level?.toUpperCase()] ?? "#94a3b8";
  const size   = isSelected ? 18 : 10;
  const pulse  = isSelected && (level === "HIGH" || level === "CRITICAL") ? "animate-pulse" : "";

  return L.divIcon({
    className: "",
    html: `
      <div style="
        width:${size}px; height:${size}px;
        background:${color};
        border-radius:50%;
        border: ${isSelected ? "2.5px solid rgba(255,255,255,0.9)" : "1.5px solid rgba(0,0,0,0.4)"};
        box-shadow: 0 0 ${isSelected ? "12px" : "4px"} ${color}80;
        transition: all 0.2s ease;
      "></div>`,
    iconSize:   [size, size],
    iconAnchor: [size / 2, size / 2],
  });
};

type MpaShape = { name: string; rings: [number, number][][] };

// Flatten Polygon + MultiPolygon features into a list of named rings for Leaflet.
function featuresToShapes(geojson: any): MpaShape[] {
  const features = geojson?.type === "FeatureCollection" ? (geojson.features ?? []) : [geojson];
  const shapes: MpaShape[] = [];
  for (const feature of features) {
    const geom = feature?.geometry;
    if (!geom) continue;
    const name = String(feature.properties?.NAME ?? "Protected Area");
    const polygons = geom.type === "MultiPolygon" ? geom.coordinates : [geom.coordinates];
    for (const polygon of polygons) {
      const outer = polygon?.[0];
      if (!outer) continue;
      shapes.push({ name, rings: [outer.map(([lon, lat]: number[]) => [lat, lon] as [number, number])] });
    }
  }
  return shapes;
}

// Loads only the MPAs inside the current viewport, refetching on pan/zoom so we
// never pull the full global WDPA set. Renders them as dashed teal polygons.
function MpaLayer({ onError }: { onError: (msg: string | null) => void }) {
  const map = useMap();
  const [mpas, setMpas] = useState<MpaShape[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refetch = () => {
    if (timer.current) clearTimeout(timer.current);
    // Debounce so a pan/zoom gesture triggers a single request.
    timer.current = setTimeout(() => {
      const b = map.getBounds();
      const bbox: [number, number, number, number] = [
        b.getWest(), b.getSouth(), b.getEast(), b.getNorth(),
      ];
      fetchMPA(bbox)
        .then((geojson) => { setMpas(featuresToShapes(geojson)); onError(null); })
        .catch(() => onError("Couldn't load protected-area boundaries."));
    }, 300);
  };

  useMapEvents({ moveend: refetch, zoomend: refetch });
  // Initial load once the map is ready.
  useEffect(() => { refetch(); return () => { if (timer.current) clearTimeout(timer.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      {mpas.map((mpa, i) => (
        <Polygon
          key={`${mpa.name}-${i}`}
          positions={mpa.rings}
          pathOptions={{ color: "#25A5A8", weight: 2, fillColor: "#1E8A8C", fillOpacity: 0.08, dashArray: "6 4" }}
        >
          <Popup className="custom-popup">
            <div className="text-sm font-semibold text-slate-800">{mpa.name}</div>
            <div className="text-xs text-slate-500">Marine Protected Area</div>
          </Popup>
        </Polygon>
      ))}
    </>
  );
}

export default function MapView({
  events, selected, onSelect, scanMode = false, scanPoint = null, onScanPick,
}: {
  events: RiskEvent[];
  selected: RiskEvent | null;
  onSelect: (e: RiskEvent) => void;
  scanMode?: boolean;
  scanPoint?: { lat: number; lon: number } | null;
  onScanPick?: (lat: number, lon: number) => void;
}) {
  const [error, setError] = useState<string | null>(null);

  return (
    <div className={`w-full h-full relative z-0 ${scanMode ? "[&_.leaflet-container]:cursor-crosshair" : ""}`}>
      {error && (
        <div className="absolute left-1/2 -translate-x-1/2 top-3 z-[1000] rounded-lg border border-ocean-700/50 bg-ocean-900/90 backdrop-blur-sm px-3 py-2 text-xs text-slate-400 shadow-lg">
          {error}
        </div>
      )}

      <MapContainer
        center={[8.5, 79.7]}
        zoom={9}
        minZoom={2}
        style={{ width: "100%", height: "100%" }}
        zoomControl={false}
        worldCopyJump={false}
        maxBounds={[[-90, -180], [90, 180]]}
        maxBoundsViscosity={1.0}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          noWrap={true}
        />
        <MpaLayer onError={setError} />

        {events.map((ev) => (
          <Marker
            key={ev.id}
            position={[ev.lat, ev.lon]}
            icon={createDotIcon(ev.risk_level, selected?.id === ev.id)}
            eventHandlers={{ click: () => onSelect(ev) }}
            zIndexOffset={selected?.id === ev.id ? 1000 : 0}
          >
            <Popup>
              <div className="text-xs">
                <div className="font-bold text-slate-200 mb-1">{ev.id}</div>
                <div className={`font-bold text-xs ${getRiskColor(ev.risk_level)}`}>
                  {ev.risk_level} · {(ev.risk_score * 100).toFixed(0)}
                </div>
                {ev.near_mpa && (
                  <div className="text-slate-400 mt-1">{ev.distance_to_mpa_km} km from MPA</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {scanPoint && <Marker position={[scanPoint.lat, scanPoint.lon]} icon={scanIcon} />}

        <ScanClickHandler active={scanMode} onPick={(lat, lon) => onScanPick?.(lat, lon)} />
        <FitBounds events={events} />
        <MapController selected={selected} />
      </MapContainer>
    </div>
  );
}
