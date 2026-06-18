import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polygon, useMap } from "react-leaflet";
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

export default function MapView({ events, selected, onSelect }: {
  events: RiskEvent[];
  selected: RiskEvent | null;
  onSelect: (e: RiskEvent) => void;
}) {
  const [mpas, setMpas] = useState<MpaShape[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    fetchMPA()
      .then((geojson) => {
        const features = geojson.type === "FeatureCollection"
          ? (geojson.features ?? [])
          : [geojson];

        // Flatten Polygon + MultiPolygon features into a list of named rings.
        const shapes: MpaShape[] = [];
        for (const feature of features) {
          const geom = feature.geometry;
          if (!geom) continue;
          const name = String(feature.properties?.NAME ?? "Protected Area");
          // Normalize to an array of polygons (each polygon = array of rings).
          const polygons =
            geom.type === "MultiPolygon" ? geom.coordinates : [geom.coordinates];
          for (const polygon of polygons) {
            const outer = polygon?.[0];
            if (!outer) continue;
            shapes.push({
              name,
              rings: [outer.map(([lon, lat]) => [lat, lon] as [number, number])],
            });
          }
        }

        if (!cancelled) {
          setMpas(shapes);
          if (shapes.length === 0) setError("Couldn't load protected-area boundaries.");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMpas([]);
          setError("Couldn't load protected-area boundaries.");
        }
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="w-full h-full relative z-0">
      {error && (
        <div className="absolute left-3 top-3 z-[1000] rounded-lg border border-ocean-700/50 bg-ocean-900/90 backdrop-blur-sm px-3 py-2 text-xs text-slate-400 shadow-lg">
          {error}
        </div>
      )}

      {/* Legend */}
      <div className="absolute right-3 top-3 z-[1000] rounded-lg border border-ocean-700/50 bg-ocean-900/90 backdrop-blur-sm px-3 py-2 shadow-lg">
        <div className="text-[9px] text-slate-500 uppercase tracking-widest mb-1.5 font-semibold">Risk Level</div>
        {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((lvl) => (
          <div key={lvl} className="flex items-center gap-1.5 text-[10px] text-slate-400 mb-1 last:mb-0">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: RISK_COLORS[lvl] }} />
            {lvl}
          </div>
        ))}
      </div>

      <MapContainer
        center={[8.5, 79.7]}
        zoom={9}
        style={{ width: "100%", height: "100%" }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />
        {mpas.map((mpa, i) => (
          <Polygon
            key={`${mpa.name}-${i}`}
            positions={mpa.rings}
            pathOptions={{
              color: "#25A5A8",
              weight: 2,
              fillColor: "#1E8A8C",
              fillOpacity: 0.08,
              dashArray: "6 4",
            }}
          >
            <Popup className="custom-popup">
              <div className="text-sm font-semibold text-slate-800">{mpa.name}</div>
              <div className="text-xs text-slate-500">Marine Protected Area</div>
            </Popup>
          </Polygon>
        ))}

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

        <MapController selected={selected} />
      </MapContainer>
    </div>
  );
}
