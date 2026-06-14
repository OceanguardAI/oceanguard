# OceanGuard AI — Frontend Team Plan (Team 1)

> **Team 1 — Frontend.** Your job: build the React dashboard that conservation officers use. Everything you display comes from the backend API at `http://localhost:8000`. Do not invent new risk formulas, new API routes, or new field names. Everything is specified here — follow it exactly.

---

## What You Deliver

A running React app at `http://localhost:5173` (dev) / port 80 (Docker) with:
- Map dashboard with Bar Reef MPA polygon + 4 coloured vessel markers
- Evidence Card panel when a marker is clicked
- Patrol Board, Daily Briefing, AI Chat
- Model Metrics with real numbers
- Responsible AI footer on every page

**Critical demo path:** Map → click bar-reef-003 marker (0.4 km from Bar Reef MPA, score 0.61 / HIGH) → Evidence Card opens → "Get AI Explanation" button → Patrol Board ranks bar-reef-003 as #1.

---

## Files You Own

```
frontend/
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js         ← required for Tailwind to work
├── tsconfig.json             ← required for TypeScript
├── index.html
├── nginx.conf                ← Docker deployment
├── Dockerfile
└── src/
    ├── main.tsx              ← React root entry point
    ├── App.tsx               ← sidebar layout + page routing
    ├── lib/
    │   ├── api.ts            ← all backend fetch calls
    │   └── riskColor.ts      ← risk level → hex color
    ├── types/
    │   └── index.ts          ← TypeScript interfaces
    └── components/
        ├── MapView.tsx
        ├── RiskTable.tsx
        ├── EvidenceCard.tsx
        ├── DailyBriefing.tsx
        ├── PatrolBoard.tsx
        ├── AskOceanGuard.tsx
        ├── ModelMetrics.tsx
        ├── DataSources.tsx
        └── ResponsibleAIFooter.tsx
```

---

## Step 1 — Setup

```bash
cd frontend
npm install
```

Verify Tailwind + Vite link:
```bash
npm run dev
# Open http://localhost:5173 — should show a page (even blank) with no build errors
```

---

## Step 2 — Config Files

### `package.json`

```json
{
  "name": "oceanguard-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "recharts": "^2.12.0",
    "lucide-react": "^0.400.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@types/leaflet": "^1.9.0",
    "typescript": "^5.4.0",
    "vite": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### `tailwind.config.js`

```js
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ocean: {
          900: "#0B1F3A",
          800: "#0F2A4A",
          700: "#1A3A5C",
        },
        teal: {
          500: "#1E8A8C",
          400: "#25A5A8",
        },
        risk: {
          low:      "#22c55e",
          medium:   "#fbbf24",
          high:     "#f97316",
          critical: "#dc2626",
        },
      },
    },
  },
  plugins: [],
};
```

### `postcss.config.js`

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

### `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  },
  "include": ["src"]
}
```

### `vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

### `index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OceanGuard AI</title>
    <!-- Leaflet CSS MUST be here — importing in JS causes map tile z-index bugs -->
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      crossorigin=""
    />
    <style>
      body { margin: 0; background: #0B1F3A; color: white; font-family: system-ui, sans-serif; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## Step 3 — TypeScript Types

### `src/types/index.ts`

```typescript
export interface RiskEvent {
  id: string;
  source: "GFW" | "YOLO_SAR";
  lat: number;
  lon: number;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  sar_confidence: number;
  image_quality: string;
  ais_matched: boolean;
  ais_data_available: boolean;
  matching_method: string;
  inside_mpa: boolean;
  near_mpa: boolean;
  mpa_name: string | null;
  distance_to_mpa_km: number | null;
  distance_from_port_km: number | null;
  nearest_port: string | null;
  timestamp: string;
  review_status: "Pending" | "Confirmed Risk" | "False Positive" | "Resolved";
  why_flagged: string;
  uncertainty: string;
  confidence_threshold: number;
  recommended_action: string;
  thumbnail: string | null;
}

export interface ModelMetrics {
  model: string;
  dataset: string;
  epochs: number;
  map50: number;
  map50_95: number;
  precision: number;
  recall: number;
  confidence_threshold: number;
  validation_scene: string;
  detections_on_real_scene: number;
  training_history: Array<{ epoch: number; map50: number; loss: number }>;
}

export interface PatrolItem {
  id: string;
  rank: number;
  risk_level: string;
  distance_to_mpa_km: number | null;
  justification: string;
}

export interface NarrateResponse {
  why_flagged: string;
  uncertainty: string;
}

export interface BriefingResponse {
  briefing: string;
}

export interface AskResponse {
  answer: string;
}
```

---

## Step 4 — Utility Helpers

### `src/lib/riskColor.ts`

```typescript
export const riskColor = (level: string): string => {
  switch (level) {
    case "CRITICAL": return "#dc2626";
    case "HIGH":     return "#f97316";
    case "MEDIUM":   return "#fbbf24";
    default:         return "#22c55e";
  }
};

export const riskBgClass = (level: string): string => {
  switch (level) {
    case "CRITICAL": return "bg-red-600 text-white";
    case "HIGH":     return "bg-orange-500 text-white";
    case "MEDIUM":   return "bg-amber-400 text-black";
    default:         return "bg-green-500 text-black";
  }
};
```

### `src/lib/api.ts`

```typescript
import type {
  RiskEvent, ModelMetrics, PatrolItem,
  NarrateResponse, BriefingResponse, AskResponse,
} from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  getRiskEvents: (params?: { source?: string; level?: string }) => {
    const qs = params
      ? "?" + new URLSearchParams(params as Record<string, string>).toString()
      : "";
    return get<RiskEvent[]>(`/risk-events${qs}`);
  },

  getRiskEvent: (id: string) =>
    get<RiskEvent>(`/risk-events/${id}`),

  postReview: (id: string, status: string) =>
    post<RiskEvent>(`/risk-events/${id}/review`, { review_status: status }),

  getMPA: () =>
    get<object>("/mpa"),

  getPorts: () =>
    get<object[]>("/ports"),

  getModelMetrics: () =>
    get<ModelMetrics>("/model-metrics"),

  narrate: (event: RiskEvent) =>
    post<NarrateResponse>("/agents/narrate", event),

  briefing: (events: RiskEvent[]) =>
    post<BriefingResponse>("/agents/briefing", events),

  patrol: (events: RiskEvent[]) =>
    post<PatrolItem[]>("/agents/patrol", events),

  ask: (question: string) =>
    post<AskResponse>("/agents/ask", { question }),
};
```

---

## Step 5 — Entry Point

### `src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `src/index.css` (Tailwind directives):
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## Step 6 — App Shell

### `src/App.tsx`

```tsx
import React, { useState } from "react";
import {
  Map, Shield, MessageSquare, FileText, BarChart2, Database,
} from "lucide-react";
import MapView from "./components/MapView";
import PatrolBoard from "./components/PatrolBoard";
import AskOceanGuard from "./components/AskOceanGuard";
import DailyBriefing from "./components/DailyBriefing";
import ModelMetrics from "./components/ModelMetrics";
import DataSources from "./components/DataSources";
import ResponsibleAIFooter from "./components/ResponsibleAIFooter";

type Page = "map" | "patrol" | "ask" | "briefing" | "metrics" | "sources";

const NAV: { id: Page; label: string; Icon: React.FC<{ size?: number }> }[] = [
  { id: "map",      label: "Map",          Icon: Map },
  { id: "patrol",   label: "Patrol Board", Icon: Shield },
  { id: "ask",      label: "Ask AI",       Icon: MessageSquare },
  { id: "briefing", label: "Briefing",     Icon: FileText },
  { id: "metrics",  label: "Metrics",      Icon: BarChart2 },
  { id: "sources",  label: "Data Sources", Icon: Database },
];

export default function App() {
  const [page, setPage] = useState<Page>("map");

  return (
    <div className="flex h-screen bg-ocean-900 text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-48 flex-shrink-0 bg-ocean-800 flex flex-col py-6">
        <div className="px-4 mb-8">
          <span className="text-teal-500 font-bold text-lg tracking-wide">
            OceanGuard
          </span>
          <span className="block text-xs text-gray-400 mt-0.5">AI · Dark Vessel</span>
        </div>
        <nav className="flex-1 space-y-1 px-2">
          {NAV.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => setPage(id)}
              className={[
                "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                page === id
                  ? "bg-teal-500 text-white"
                  : "text-gray-300 hover:bg-ocean-700",
              ].join(" ")}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6">
          {page === "map"      && <MapView />}
          {page === "patrol"   && <PatrolBoard />}
          {page === "ask"      && <AskOceanGuard />}
          {page === "briefing" && <DailyBriefing />}
          {page === "metrics"  && <ModelMetrics />}
          {page === "sources"  && <DataSources />}
        </div>
        <ResponsibleAIFooter />
      </main>
    </div>
  );
}
```

---

## Step 7 — Components

### `src/components/MapView.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Polygon, Popup, useMap } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import { api } from "../lib/api";
import { riskColor } from "../lib/riskColor";
import type { RiskEvent } from "../types";
import EvidenceCard from "./EvidenceCard";
import RiskTable from "./RiskTable";

// Bar Reef MPA polygon — GeoJSON is [lon, lat]; Leaflet needs [lat, lon]
const BAR_REEF_COORDS: LatLngExpression[] = [
  [8.26746323, 79.73550022],
  [8.32294782, 79.76349894],
  [8.53409068, 79.78222715],
  [8.53142862, 79.68343578],
  [8.26487243, 79.68286497],
  [8.26746323, 79.73550022],
];

function FitBounds({ events }: { events: RiskEvent[] }) {
  const map = useMap();
  useEffect(() => {
    if (events.length > 0) {
      map.setView([8.5, 79.7], 9);
    }
  }, [map, events]);
  return null;
}

export default function MapView() {
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [selected, setSelected] = useState<RiskEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRiskEvents({ source: "GFW" })
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const high    = events.filter((e) => e.risk_level === "HIGH" || e.risk_level === "CRITICAL");
  const pending = events.filter((e) => e.review_status === "Pending");

  if (loading) return <p className="text-gray-400">Loading map data...</p>;
  if (error)   return <p className="text-red-400">Error: {error}</p>;

  return (
    <div className="flex flex-col gap-4">
      {/* Stat row */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Dark Vessel Detections", value: events.length },
          { label: "HIGH / CRITICAL Risk",   value: high.length },
          { label: "MPA Monitored",           value: 1 },
        ].map(({ label, value }) => (
          <div key={label} className="bg-ocean-800 rounded-lg px-4 py-3">
            <p className="text-2xl font-bold text-teal-400">{value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Map */}
      <div className="rounded-xl overflow-hidden h-[480px] relative">
        <MapContainer
          center={[8.5, 79.7]}
          zoom={9}
          style={{ width: "100%", height: "100%" }}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            subdomains="abcd"
            maxZoom={19}
          />
          <FitBounds events={events} />

          {/* MPA polygon */}
          <Polygon
            positions={BAR_REEF_COORDS}
            pathOptions={{
              color: "#1E8A8C",
              fillColor: "#1E8A8C",
              fillOpacity: 0.15,
              weight: 2,
            }}
          >
            <Popup>Bar Reef Marine Sanctuary</Popup>
          </Polygon>

          {/* Risk event markers */}
          {events.map((event) => (
            <CircleMarker
              key={event.id}
              center={[event.lat, event.lon]}
              radius={event.risk_level === "HIGH" || event.risk_level === "CRITICAL" ? 14 : 10}
              pathOptions={{
                color: riskColor(event.risk_level),
                fillColor: riskColor(event.risk_level),
                fillOpacity: 0.85,
                weight: 2,
              }}
              eventHandlers={{ click: () => setSelected(event) }}
            >
              <Popup>
                <strong>{event.id}</strong><br />
                Risk: {event.risk_level} ({event.risk_score})
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>

        {/* Evidence card overlay */}
        {selected && (
          <div className="absolute top-0 right-0 h-full w-96 overflow-y-auto z-[1000]">
            <EvidenceCard
              event={selected}
              onClose={() => setSelected(null)}
              onReviewUpdate={(updated) => {
                setEvents((prev) =>
                  prev.map((e) => (e.id === updated.id ? updated : e))
                );
                setSelected(updated);
              }}
            />
          </div>
        )}
      </div>

      {/* Table of events */}
      <RiskTable events={events} onSelect={setSelected} />
    </div>
  );
}
```

### `src/components/EvidenceCard.tsx`

```tsx
import React, { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { riskBgClass } from "../lib/riskColor";
import type { RiskEvent } from "../types";

interface Props {
  event: RiskEvent;
  onClose: () => void;
  onReviewUpdate: (updated: RiskEvent) => void;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-white mt-0.5 font-medium">{value ?? "—"}</p>
    </div>
  );
}

const REVIEW_STATUSES = ["Confirmed Risk", "False Positive", "Resolved"] as const;

export default function EvidenceCard({ event, onClose, onReviewUpdate }: Props) {
  const [narrating, setNarrating] = useState(false);
  const [narration, setNarration] = useState<{ why: string; uncertainty: string } | null>(null);
  const [narrateError, setNarrateError] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState<string | null>(null);

  const handleNarrate = async () => {
    setNarrating(true);
    setNarrateError(null);
    try {
      const resp = await api.narrate(event);
      setNarration({ why: resp.why_flagged, uncertainty: resp.uncertainty });
    } catch (e) {
      setNarrateError("Could not get AI explanation. Please try again.");
    } finally {
      setNarrating(false);
    }
  };

  const handleReview = async (status: string) => {
    setReviewing(status);
    try {
      const updated = await api.postReview(event.id, status);
      onReviewUpdate(updated);
    } catch {
      // optimistic fallback
      onReviewUpdate({ ...event, review_status: status as RiskEvent["review_status"] });
    } finally {
      setReviewing(null);
    }
  };

  return (
    <div className="bg-ocean-800 border border-ocean-700 h-full flex flex-col shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ocean-700">
        <div className="flex items-center gap-2">
          <span className="font-mono text-teal-400 text-sm font-bold">{event.id}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${riskBgClass(event.risk_level)}`}>
            {event.risk_level}
          </span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {/* Risk score */}
        <div className="flex items-center gap-3">
          <div className="text-4xl font-bold text-white">{event.risk_score.toFixed(2)}</div>
          <div>
            <p className="text-xs text-gray-400">Risk Score</p>
            <p className={`text-sm font-semibold ${riskBgClass(event.risk_level)} px-2 py-0.5 rounded-full inline-block`}>
              {event.risk_level}
            </p>
          </div>
        </div>

        {/* Field grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-3">
          <Field label="Source"        value={event.source} />
          <Field label="Timestamp"     value={new Date(event.timestamp).toLocaleString()} />
          <Field label="Latitude"      value={event.lat.toFixed(5)} />
          <Field label="Longitude"     value={event.lon.toFixed(5)} />
          <Field label="SAR Confidence" value={`${(event.sar_confidence * 100).toFixed(0)}%`} />
          <Field label="Image Quality" value={event.image_quality} />
          <Field label="AIS Matched"   value={event.ais_matched ? "✓ Yes" : "✗ No"} />
          <Field label="AIS Available" value={event.ais_data_available ? "Yes" : "No"} />
          <Field label="Inside MPA"    value={event.inside_mpa ? "✓ Yes" : "✗ No"} />
          <Field label="Near MPA (≤5km)" value={event.near_mpa ? "✓ Yes" : "✗ No"} />
          <Field label="MPA Name"      value={event.mpa_name} />
          <Field label="Dist. to MPA"  value={event.distance_to_mpa_km != null ? `${event.distance_to_mpa_km} km` : "N/A"} />
          <Field label="Nearest Port"  value={event.nearest_port} />
          <Field label="Dist. to Port" value={event.distance_from_port_km != null ? `${event.distance_from_port_km} km` : "N/A"} />
          <Field label="Review Status" value={event.review_status} />
          <Field label="Conf. Threshold" value={event.confidence_threshold} />
        </div>

        <Field label="Matching Method" value={event.matching_method} />
        <Field label="Recommended Action" value={event.recommended_action} />

        {/* AI Explanation */}
        <div className="border border-teal-500/30 rounded-lg p-3 space-y-2">
          <p className="text-xs text-teal-400 font-semibold uppercase tracking-wide">
            AI Explanation (Claude)
          </p>
          {narration ? (
            <>
              <p className="text-sm text-gray-200">{narration.why}</p>
              <p className="text-xs text-gray-400 mt-1">
                <span className="font-semibold text-amber-400">Uncertainty:</span> {narration.uncertainty}
              </p>
            </>
          ) : narrateError ? (
            <p className="text-xs text-red-400">{narrateError}</p>
          ) : (
            <button
              onClick={handleNarrate}
              disabled={narrating}
              className="flex items-center gap-2 text-sm bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              {narrating ? <><Loader2 size={14} className="animate-spin" /> Generating…</> : "Get AI Explanation"}
            </button>
          )}
          <p className="text-xs text-gray-500">
            AI-generated — for context only. All enforcement decisions are made by conservation officers.
          </p>
        </div>

        {/* Review buttons */}
        <div className="space-y-2">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Mark Review Status</p>
          <div className="flex flex-wrap gap-2">
            {REVIEW_STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => handleReview(status)}
                disabled={reviewing !== null || event.review_status === status}
                className={[
                  "text-xs px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-40",
                  status === "Confirmed Risk"
                    ? "border-red-500 text-red-400 hover:bg-red-500/20"
                    : status === "False Positive"
                    ? "border-green-500 text-green-400 hover:bg-green-500/20"
                    : "border-gray-500 text-gray-400 hover:bg-gray-500/20",
                  event.review_status === status ? "opacity-40 cursor-not-allowed" : "",
                ].join(" ")}
              >
                {reviewing === status ? "Saving…" : status}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

### `src/components/RiskTable.tsx`

```tsx
import React, { useState } from "react";
import { riskBgClass } from "../lib/riskColor";
import type { RiskEvent } from "../types";

interface Props {
  events: RiskEvent[];
  onSelect: (event: RiskEvent) => void;
}

type SortKey = "risk_score" | "distance_to_mpa_km" | "timestamp";

export default function RiskTable({ events, onSelect }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = [...events].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return sortAsc ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  const toggle = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const th = (label: string, key?: SortKey) => (
    <th
      className={`px-4 py-2 text-xs text-gray-400 uppercase tracking-wide text-left ${key ? "cursor-pointer hover:text-white" : ""}`}
      onClick={() => key && toggle(key)}
    >
      {label} {key && sortKey === key && (sortAsc ? "↑" : "↓")}
    </th>
  );

  if (events.length === 0) return null;

  return (
    <div className="bg-ocean-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="border-b border-ocean-700">
          <tr>
            {th("ID")}
            {th("Source")}
            {th("Risk", "risk_score")}
            {th("Lat / Lon")}
            {th("Dist. MPA", "distance_to_mpa_km")}
            {th("AIS")}
            {th("Timestamp", "timestamp")}
            {th("Status")}
          </tr>
        </thead>
        <tbody>
          {sorted.map((e) => (
            <tr
              key={e.id}
              className="border-b border-ocean-700/50 hover:bg-ocean-700 cursor-pointer transition-colors"
              onClick={() => onSelect(e)}
            >
              <td className="px-4 py-2 font-mono text-teal-400 text-xs">{e.id}</td>
              <td className="px-4 py-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${e.source === "GFW" ? "bg-blue-700" : "bg-purple-700"}`}>
                  {e.source}
                </span>
              </td>
              <td className="px-4 py-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${riskBgClass(e.risk_level)}`}>
                  {e.risk_level}
                </span>
                <span className="ml-1 text-gray-300">{e.risk_score.toFixed(2)}</span>
              </td>
              <td className="px-4 py-2 font-mono text-xs text-gray-300">
                {e.lat.toFixed(4)}, {e.lon.toFixed(4)}
              </td>
              <td className="px-4 py-2 text-gray-300">
                {e.distance_to_mpa_km != null ? `${e.distance_to_mpa_km} km` : "—"}
              </td>
              <td className="px-4 py-2 text-gray-300">
                {e.ais_matched ? "✓" : "✗"}
              </td>
              <td className="px-4 py-2 text-xs text-gray-400">
                {new Date(e.timestamp).toLocaleDateString()}
              </td>
              <td className="px-4 py-2 text-xs text-gray-400">{e.review_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### `src/components/EvidenceCard.tsx` is defined above.

### `src/components/DailyBriefing.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import type { RiskEvent } from "../types";

export default function DailyBriefing() {
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [briefing, setBriefing] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const evts = await api.getRiskEvents({ source: "GFW" });
      setEvents(evts);
      const resp = await api.briefing(evts);
      setBriefing(resp.briefing);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load briefing");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Daily Briefing</h2>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 text-sm text-teal-400 hover:text-teal-300 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          Generating briefing…
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : (
        <div className="bg-teal-500/10 border border-teal-500/30 rounded-xl p-6">
          <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">{briefing}</p>
        </div>
      )}

      {events.length > 0 && (
        <p className="text-xs text-gray-500">
          Based on {events.length} GFW SAR dark-vessel detections near Bar Reef MPA.
        </p>
      )}
    </div>
  );
}
```

### `src/components/PatrolBoard.tsx`

```tsx
import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { riskBgClass } from "../lib/riskColor";
import type { RiskEvent, PatrolItem } from "../types";

export default function PatrolBoard() {
  const [items, setItems] = useState<PatrolItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const events = await api.getRiskEvents({ source: "GFW" });
        const patrol = await api.patrol(events);
        setItems(patrol);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load patrol plan");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Patrol Recommendation Board</h2>
      <p className="text-xs text-gray-400">
        AI-suggested patrol priority order. Final decisions are made by conservation officers.
      </p>

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400">
          <Loader2 size={16} className="animate-spin" /> Generating patrol plan…
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex gap-4 bg-ocean-800 rounded-xl px-5 py-4 border border-ocean-700"
            >
              <div className="text-3xl font-bold text-gray-600 w-8 flex-shrink-0">
                {item.rank}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-teal-400 text-sm">{item.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${riskBgClass(item.risk_level)}`}>
                    {item.risk_level}
                  </span>
                  {item.distance_to_mpa_km != null && (
                    <span className="text-xs text-gray-400">
                      {item.distance_to_mpa_km} km from MPA
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-300">{item.justification}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### `src/components/AskOceanGuard.tsx`

```tsx
import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { api } from "../lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTED = [
  "Which detection is highest risk?",
  "How far is bar-reef-003 from the MPA?",
  "What does dark vessel mean?",
];

export default function AskOceanGuard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (question: string) => {
    if (!question.trim() || sending) return;
    const userMsg: Message = { role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);
    try {
      const resp = await api.ask(question);
      setMessages((prev) => [...prev, { role: "assistant", text: resp.answer }]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, I couldn't process that question right now." },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-160px)]">
      <h2 className="text-lg font-semibold mb-3">Ask OceanGuard</h2>

      {/* Suggested chips */}
      <div className="flex flex-wrap gap-2 mb-4">
        {SUGGESTED.map((q) => (
          <button
            key={q}
            onClick={() => send(q)}
            className="text-xs bg-ocean-700 hover:bg-teal-500/20 border border-ocean-600 hover:border-teal-500 text-gray-300 hover:text-white px-3 py-1.5 rounded-full transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Thread */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.length === 0 && (
          <p className="text-gray-500 text-sm text-center mt-8">
            Ask anything about the detections, the MPA, or the risk scores.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={[
                "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
                m.role === "user"
                  ? "bg-teal-500 text-white rounded-br-sm"
                  : "bg-ocean-800 text-gray-200 rounded-bl-sm border border-ocean-700",
              ].join(" ")}
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-ocean-800 border border-ocean-700 rounded-2xl rounded-bl-sm px-4 py-2.5">
              <Loader2 size={14} className="animate-spin text-gray-400" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Type a question…"
          className="flex-1 bg-ocean-800 border border-ocean-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
        />
        <button
          onClick={() => send(input)}
          disabled={!input.trim() || sending}
          className="bg-teal-500 hover:bg-teal-400 disabled:opacity-40 text-white px-4 py-2.5 rounded-xl transition-colors"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
```

### `src/components/ModelMetrics.tsx`

```tsx
import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from "recharts";
import { api } from "../lib/api";
import type { ModelMetrics as Metrics } from "../types";

const METRIC_BARS = [
  { key: "precision", label: "Precision", value: 0.830 },
  { key: "recall",    label: "Recall",    value: 0.818 },
  { key: "map50",     label: "mAP50",     value: 0.838 },
  { key: "map50_95",  label: "mAP50-95",  value: 0.579 },
];

export default function ModelMetrics() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getModelMetrics().then(setMetrics).catch((e) => setError(e.message));
  }, []);

  // Stat card row uses hardcoded values — if API fails, we still show them
  const statCards = [
    { label: "Model",       value: metrics?.model ?? "YOLO11n" },
    { label: "mAP50",       value: metrics ? metrics.map50.toFixed(3) : "0.838" },
    { label: "Detections",  value: metrics?.detections_on_real_scene ?? 122 },
    { label: "Scene",       value: "xView3 Gulf of Guinea" },
    { label: "Dataset",     value: metrics?.dataset ?? "HRSID 2857/715" },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Model Metrics — Proof A</h2>
      <p className="text-sm text-gray-400">
        YOLO11n trained on HRSID, validated on real xView3 SAR scene (590dd08f71056cacv, Gulf of Guinea).
      </p>

      {/* Stat row */}
      <div className="grid grid-cols-5 gap-3">
        {statCards.map(({ label, value }) => (
          <div key={label} className="bg-ocean-800 rounded-xl px-4 py-3 text-center">
            <p className="text-xl font-bold text-teal-400">{value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {error && <p className="text-amber-400 text-sm">Could not load live metrics: {error}. Showing hardcoded values.</p>}

      {/* Bar chart */}
      <div className="bg-ocean-800 rounded-xl p-4">
        <p className="text-sm font-semibold mb-3 text-gray-300">Validation Metrics</p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={METRIC_BARS.map((m) => ({
              name: m.label,
              value: metrics ? (metrics as Record<string, number>)[m.key] ?? m.value : m.value,
            }))}
            margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" />
            <XAxis dataKey="name" tick={{ fill: "#9CA3AF", fontSize: 12 }} />
            <YAxis domain={[0, 1]} tick={{ fill: "#9CA3AF", fontSize: 12 }} />
            <Tooltip
              contentStyle={{ background: "#0F2A4A", border: "1px solid #1A3A5C", borderRadius: 8 }}
              labelStyle={{ color: "#9CA3AF" }}
              formatter={(v: number) => v.toFixed(3)}
            />
            <Bar dataKey="value" fill="#1E8A8C" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Training curve */}
      {metrics?.training_history && (
        <div className="bg-ocean-800 rounded-xl p-4">
          <p className="text-sm font-semibold mb-3 text-gray-300">Training Curve (mAP50 vs Epoch)</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={metrics.training_history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" />
              <XAxis dataKey="epoch" tick={{ fill: "#9CA3AF", fontSize: 12 }} />
              <YAxis domain={[0, 1]} tick={{ fill: "#9CA3AF", fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: "#0F2A4A", border: "1px solid #1A3A5C", borderRadius: 8 }}
                formatter={(v: number) => v.toFixed(3)}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="map50"
                stroke="#1E8A8C"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="mAP50"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
```

### `src/components/DataSources.tsx`

```tsx
import React from "react";

const SOURCES = [
  {
    name: "HRSID",
    description: "High-Resolution SAR Image Dataset for vessel detection. 2572 images, 16951 ship instances. Used to train YOLO11n.",
    url: "https://github.com/chaozhong2010/HRSID",
    type: "Training Data",
  },
  {
    name: "xView3-SAR",
    description: "Real Sentinel-1 SAR scenes with vessel labels. Scene 590dd08f71056cacv used for model validation — 122 detections.",
    url: "https://iuu.xview.us",
    type: "Validation Data",
  },
  {
    name: "Global Fishing Watch",
    description: "SAR-based dark vessel detections (unmatched AIS). 4 detections near Bar Reef MPA, all with matched=false.",
    url: "https://globalfishingwatch.org",
    type: "Dark Vessel Data",
  },
  {
    name: "WDPA — Bar Reef",
    description: "World Database on Protected Areas. Bar Reef Marine Sanctuary boundary polygon (WDPAID: 4783), Sri Lanka.",
    url: "https://www.protectedplanet.net",
    type: "MPA Boundary",
  },
  {
    name: "OpenStreetMap / Overpass",
    description: "Port and marina locations near Bar Reef from OSM Overpass API. Used for distance-to-port enrichment.",
    url: "https://overpass-api.de",
    type: "Port Data",
  },
];

export default function DataSources() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Data Sources</h2>
      <p className="text-sm text-gray-400">
        All data is either open-access or cached from authorised API calls. No vessel identities are processed.
      </p>
      <div className="grid grid-cols-1 gap-4">
        {SOURCES.map((s) => (
          <div key={s.name} className="bg-ocean-800 rounded-xl px-5 py-4 border border-ocean-700">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">{s.name}</p>
                <span className="text-xs text-teal-400">{s.type}</span>
                <p className="text-sm text-gray-400 mt-1">{s.description}</p>
              </div>
              <a
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-teal-400 hover:underline whitespace-nowrap"
              >
                Visit →
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### `src/components/ResponsibleAIFooter.tsx`

```tsx
import React from "react";

export default function ResponsibleAIFooter() {
  return (
    <footer className="bg-ocean-800 border-t border-ocean-700 px-6 py-2 flex items-center gap-4">
      <span className="text-teal-500 text-xs font-semibold uppercase tracking-wider">
        Responsible AI
      </span>
      <span className="text-xs text-gray-400">
        OceanGuard flags vessel detections for human review. It does not make accusations,
        identify individuals, or trigger enforcement. All decisions are made by conservation officers.
      </span>
    </footer>
  );
}
```

---

## Step 8 — Dockerfile + nginx.conf

### `Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### `nginx.conf`

```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Step 9 — Environment Variable

For development, no `.env` file is needed — the default `http://localhost:8000` works.

For Docker/production, create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

---

## Step 10 — Verification Checklist

Before you declare the frontend done:

- [ ] `npm run dev` starts without errors
- [ ] `npm run build` succeeds (TypeScript + Vite both pass)
- [ ] Map shows dark CartoDB tile layer (no API key error)
- [ ] Bar Reef MPA polygon appears as teal outline on map
- [ ] 4 GFW markers appear at correct lat/lon with correct colours (3 amber, 1 orange)
- [ ] Clicking `bar-reef-003` marker opens EvidenceCard on the right
- [ ] EvidenceCard shows `risk_score: 0.61`, `risk_level: HIGH`
- [ ] "Get AI Explanation" button calls `/agents/narrate` and shows text
- [ ] Review buttons call `/risk-events/bar-reef-003/review` and update status
- [ ] PatrolBoard shows `bar-reef-003` as rank 1
- [ ] ModelMetrics shows `mAP50: 0.838` and `122 detections`
- [ ] ResponsibleAIFooter visible on every page — never hidden
- [ ] App does not crash when backend is unreachable (shows error messages instead)
- [ ] `docker build -t oceanguard-frontend .` succeeds

---

## Common Problems

| Problem | Cause | Fix |
|---|---|---|
| Map doesn't render (white box) | Missing Leaflet CSS | Confirm `<link>` tag in `index.html` references Leaflet 1.9.4 CSS |
| Map renders but is black | `h-[480px]` missing on MapContainer | Always give MapContainer a fixed height |
| `window is not defined` | Leaflet tries to access DOM at import time | Use `react-leaflet` (it handles this); never `import L from 'leaflet'` directly in module scope |
| Tailwind classes not working | `postcss.config.js` missing | Create it with tailwindcss + autoprefixer plugins |
| `Cannot find module '../types'` | Wrong relative import path | Use `../types` from `components/`, `./types` from `src/` |
| TypeScript error on `null` | Strict mode | Use `?? "—"` for null fields, `?.` for optional chaining |
| CORS error from backend | Backend CORS not set | Tell backend team — they must allow `http://localhost:5173` |
| `api.patrol(events)` returns wrong shape | Backend returns different key names | Check backend plan — PatrolItem must have `{id, rank, risk_level, distance_to_mpa_km, justification}` |

---

## Backend API Quick Reference

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/risk-events` | `?source=GFW&level=HIGH` (optional) | `RiskEvent[]` |
| GET | `/risk-events/{id}` | — | `RiskEvent` |
| POST | `/risk-events/{id}/review` | `{"review_status": "Confirmed Risk"}` | updated `RiskEvent` |
| GET | `/mpa` | — | GeoJSON Feature |
| GET | `/model-metrics` | — | `ModelMetrics` |
| POST | `/agents/narrate` | `RiskEvent` | `{why_flagged, uncertainty}` |
| POST | `/agents/briefing` | `RiskEvent[]` | `{briefing: string}` |
| POST | `/agents/patrol` | `RiskEvent[]` | `PatrolItem[]` |
| POST | `/agents/ask` | `{question: string}` | `{answer: string}` |

---

## What You Do NOT Own

- Do NOT call the GFW API directly — use the backend
- Do NOT implement the risk scoring formula — the backend owns it
- Do NOT change field names in API calls — the backend team's routes must match exactly
- Do NOT add extra pages or routes not listed here
- Do NOT hide `ResponsibleAIFooter` on any page
