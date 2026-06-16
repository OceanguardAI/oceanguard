import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polygon, useMap } from "react-leaflet";
import L from "leaflet";
import { RiskEvent } from "../types";
import { fetchMPA } from "../lib/api";
import { getRiskColor } from "../lib/riskColor";

const MapController = ({ selected }: { selected: RiskEvent | null }) => {
  const map = useMap();
  useEffect(() => {
    if (selected) {
      map.setView([selected.lat, selected.lon], 11, { animate: true });
    }
  }, [selected, map]);
  return null;
};

// Custom div icon for dots
const createDotIcon = (level: string, isSelected: boolean) => {
  let color = "#22c55e"; // low
  if (level === "MEDIUM") color = "#fbbf24";
  if (level === "HIGH") color = "#f97316";
  if (level === "CRITICAL") color = "#dc2626";

  const size = isSelected ? 16 : 10;
  const border = isSelected ? "border-2 border-white" : "border border-ocean-900";
  const zIndexOffset = isSelected ? 1000 : 0;
  
  // Custom marker animation for selected items
  const pulseClass = isSelected && (level === "HIGH" || level === "CRITICAL") ? "animate-pulse" : "";

  return L.divIcon({
    className: "custom-div-icon",
    html: `<div class="rounded-full shadow-lg ${border} ${pulseClass}" style="background-color: ${color}; width: ${size}px; height: ${size}px;"></div>`,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
  });
};

export default function MapView({ events, selected, onSelect }: { 
  events: RiskEvent[]; 
  selected: RiskEvent | null;
  onSelect: (e: RiskEvent) => void;
}) {
  const [mpaCoords, setMpaCoords] = useState<[number, number][][]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    fetchMPA()
      .then((geojson) => {
        const geometry = geojson.type === "FeatureCollection"
          ? geojson.features?.[0]?.geometry
          : geojson.geometry;

        if (!geometry?.coordinates?.[0]) {
          if (!cancelled) {
            setMpaCoords([]);
            setError("Couldn't load the Bar Reef boundary.");
          }
          return;
        }

        const poly = geometry.coordinates[0].map(([lon, lat]) => [lat, lon] as [number, number]);
        if (!cancelled) {
          setMpaCoords([poly]);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMpaCoords([]);
          setError("Couldn't load the Bar Reef boundary.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="w-full h-full relative z-0">
      {error && (
        <div className="absolute left-4 top-4 z-[1000] rounded-md border border-risk-high/30 bg-ocean-900/90 px-3 py-2 text-xs text-slate-200">
          {error}
        </div>
      )}
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
        
        {mpaCoords.length > 0 && (
          <Polygon 
            positions={mpaCoords} 
            pathOptions={{ color: "#25A5A8", weight: 2, fillColor: "#1E8A8C", fillOpacity: 0.1 }}
          />
        )}

        {events.map((ev) => (
          <Marker 
            key={ev.id} 
            position={[ev.lat, ev.lon]}
            icon={createDotIcon(ev.risk_level, selected?.id === ev.id)}
            eventHandlers={{ click: () => onSelect(ev) }}
            zIndexOffset={selected?.id === ev.id ? 1000 : 0}
          >
            <Popup className="custom-popup">
              <div className="text-sm font-semibold text-slate-800">{ev.id}</div>
              <div className={`text-xs font-bold ${getRiskColor(ev.risk_level)}`}>{ev.risk_level} RISK</div>
            </Popup>
          </Marker>
        ))}

        <MapController selected={selected} />
      </MapContainer>
    </div>
  );
}
