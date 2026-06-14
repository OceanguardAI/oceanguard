# OceanGuard AI — Frontend Team Plan

> **Team 1 — Frontend.** Your job: build the React dashboard that conservation officers use. Everything you display comes from the backend API at `http://localhost:8000`.

---

## Your Deliverable

A running React app at `http://localhost:5173` with the full dashboard: map, evidence cards, patrol board, AI chat, model metrics.

**Critical demo path:** Map → click bar-reef-003 marker (0.4 km from Bar Reef MPA, score 0.61 / HIGH) → Evidence Card opens with "Get AI Explanation" → Patrol Board ranks it #1.

---

## Files You Own

```
frontend/
├── package.json                  ← implement
├── vite.config.ts                ← implement
├── tailwind.config.js            ← implement
├── index.html                    ← implement
├── nginx.conf                    ← implement (for Docker)
├── Dockerfile                    ← implement
└── src/
    ├── main.tsx                  ← implement
    ├── App.tsx                   ← implement
    ├── lib/
    │   └── api.ts                ← implement (all backend calls)
    ├── types/
    │   └── index.ts              ← implement (TypeScript types)
    └── components/
        ├── MapView.tsx           ← implement
        ├── RiskTable.tsx         ← implement
        ├── EvidenceCard.tsx      ← implement
        ├── DailyBriefing.tsx     ← implement
        ├── PatrolBoard.tsx       ← implement
        ├── AskOceanGuard.tsx     ← implement
        ├── ModelMetrics.tsx      ← implement
        ├── DataSources.tsx       ← implement
        └── ResponsibleAIFooter.tsx ← implement
```

---

## Setup

```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
# Backend must be running at http://localhost:8000
```

---

## `package.json`

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

---

## Design System

### Color Palette (add to `tailwind.config.js`)

```js
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ocean: {
          900: "#0B1F3A",   // main background
          800: "#0F2A4A",   // sidebar/card background
          700: "#1A3A5C",   // hover states
        },
        teal: {
          500: "#1E8A8C",   // primary accent
          400: "#25A5A8",   // hover accent
        },
        risk: {
          low:      "#22c55e",   // green-500
          medium:   "#fbbf24",   // amber-400
          high:     "#f97316",   // orange-500
          critical: "#dc2626",   // red-600
        }
      }
    }
  },
  plugins: []
}
```

### Risk Color Helper

```typescript
// src/lib/riskColor.ts
export const riskColor = (level: string): string => {
  switch (level) {
    case "CRITICAL": return "#dc2626";
    case "HIGH":     return "#f97316";
    case "MEDIUM":   return "#fbbf24";
    default:         return "#22c55e";
  }
};
```

---

## `src/types/index.ts`

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
```

---

## `src/lib/api.ts`

```typescript
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  getRiskEvents: (params?: { source?: string; level?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return get<RiskEvent[]>(`/risk-events${q ? "?" + q : ""}`);
  },
  getRiskEvent: (id: string) => get<RiskEvent>(`/risk-events/${id}`),
  postReview: (id: string, status: string) =>
    post(`/risk-events/${id}/review`, { review_status: status }),
  getMPA: () => get<object>("/mpa"),
  getPorts: () => get<object[]>("/ports"),
  getModelMetrics: () => get<ModelMetrics>("/model-metrics"),
  narrate: (event: RiskEvent) =>
    post<{ why_flagged: string; uncertainty: string }>("/agents/narrate", event),
  briefing: (events: RiskEvent[]) =>
    post<{ briefing: string }>("/agents/briefing", events),
  patrol: (events: RiskEvent[]) =>
    post<PatrolItem[]>("/agents/patrol", events),
  ask: (question: string) =>
    post<{ answer: string }>("/agents/ask", { question }),
};
```

Import `RiskEvent`, `ModelMetrics`, `PatrolItem` from `../types/index`.

---

## `src/App.tsx`

Sidebar navigation + page rendering. No external router — use `useState` for current page.

**Pages:** `"map"` | `"patrol"` | `"ask"` | `"briefing"` | `"metrics"` | `"sources"`

**Sidebar items** (lucide-react icons):
- Map (Map icon) → MapView
- Patrol Board (Shield icon)
- Ask OceanGuard (MessageSquare icon)
- Daily Briefing (FileText icon)
- Model Metrics (BarChart2 icon)
- Data Sources (Database icon)

**Layout:**
```
┌─────────┬──────────────────────────────────────────┐
│ sidebar │  main content area                        │
│ (navy)  │  (ocean-900 bg)                           │
│         │                                           │
│ icons + │  <active page component>                  │
│ labels  │                                           │
│         │  ─────────────────────────────────────── │
│         │  <ResponsibleAIFooter />                  │
└─────────┴──────────────────────────────────────────┘
```

---

## Component Specs

### `MapView.tsx`

```
┌─────────────────────────────────────────┐
│  4 Dark Vessel Detections  1 HIGH Risk  1 MPA Monitored  │  ← stat row
├─────────────────────────────────────────┤
│                                         │
│     [Leaflet Map — dark tiles]          │
│                                         │
│  ▓ Bar Reef MPA polygon (teal outline)  │
│  ● HIGH marker (orange)                 │
│  ● MEDIUM markers (amber, x3)           │
│                                         │
└─────────────────────────────────────────┘
    [RiskTable below map]
```

**Implementation:**
- Tile layer: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`
- Center on Bar Reef: `[8.5, 79.7]`, zoom 10
- MPA polygon from `api.getMPA()` → `<Polygon>` positions=`feature.geometry.coordinates[0].map(([lon,lat]) => [lat,lon])`, color teal `#1E8A8C`, fillOpacity 0.15
- Events from `api.getRiskEvents({ source: "GFW" })` → `<CircleMarker>` at `[event.lat, event.lon]`, radius 10, color from `riskColor(event.risk_level)`, onClick → `setSelectedEvent(event)`
- When `selectedEvent` is set → render `<EvidenceCard event={selectedEvent} onClose={() => setSelectedEvent(null)} />`

### `EvidenceCard.tsx`

Slide-in panel from the right. Full event detail + AI explanation + review buttons.

**Fields to display (two-column grid):**
- Risk Score + colored badge
- Source (GFW / YOLO_SAR)
- Coordinates
- SAR Confidence
- Image Quality
- AIS Matched / AIS Data Available
- Matching Method
- Inside MPA / Near MPA
- MPA Name
- Distance to MPA
- Distance from Port / Nearest Port
- Timestamp
- Review Status

**"Get AI Explanation" button:**
- Calls `api.narrate(event)` on click
- Shows spinner while loading
- Displays `why_flagged` and `uncertainty` in a teal-bordered box
- Button disabled while loading

**Review buttons (3):**
- "Confirmed Risk" (red border)
- "False Positive" (green border)
- "Resolved" (gray border)
- Each calls `api.postReview(event.id, status)` → optimistic UI update on `review_status`

### `DailyBriefing.tsx`

- Loads `api.briefing(gfwEvents)` on mount
- Shows spinner → then briefing text in a teal banner
- "Refresh" button re-fetches
- Collapsible (collapsed by default on mobile)

### `PatrolBoard.tsx`

- Loads `api.patrol(gfwEvents)` on mount (or "Generate Patrol Plan" button)
- Numbered list: rank, event ID, risk badge, distance to MPA, justification text
- Clicking a row highlights that marker on the map (emit to parent if needed)

### `AskOceanGuard.tsx`

**Layout:**
```
┌──────────────────────────────────┐
│  Ask OceanGuard                  │
│  [suggested question chips]      │
├──────────────────────────────────┤
│  message thread                  │
│  (user msgs right, AI left)      │
├──────────────────────────────────┤
│  [text input] [Send button]      │
└──────────────────────────────────┘
```

**Suggested questions (chips):**
- "Which detection is highest risk?"
- "How far is bar-reef-003 from the MPA?"
- "What does dark vessel mean?"

Each chip pre-fills the input and submits. Calls `api.ask(question)` → appends answer to thread.

### `ModelMetrics.tsx`

**Recharts components:**
1. `BarChart` — metrics bar chart:
   - bars: Precision (0.830), Recall (0.818), mAP50 (0.838), mAP50-95 (0.579)
   - x-axis: metric name, y-axis: 0–1
   - Colors: teal

2. `LineChart` — training curve:
   - x-axis: epoch, y-axis: mAP50
   - data from `metrics.training_history`

3. Stat cards row:
   - "YOLO11n" model name
   - "mAP50 0.838"
   - "122 detections on xView3"
   - "Scene: 590dd08f71056cacv (Gulf of Guinea)"
   - "Dataset: HRSID 2857/715 train/val"

### `RiskTable.tsx`

Sortable table of all events. Columns:
- ID
- Source badge (GFW = blue, YOLO_SAR = purple)
- Lat / Lon
- Risk Level badge (colored)
- Distance to MPA
- AIS Matched (✓ / ✗)
- Timestamp
- Review Status

Click row → open EvidenceCard.

### `DataSources.tsx`

Static cards (no API calls) describing each data source:

| Source | Description | Link |
|---|---|---|
| HRSID | Training dataset for vessel detection model | github.com/chaozhong2010/HRSID |
| xView3-SAR | Real SAR scene for model validation (122 detections) | iuu.xview.us |
| Global Fishing Watch | SAR-derived dark-vessel detections near Bar Reef | globalfishingwatch.org |
| WDPA | Bar Reef Marine Sanctuary boundary polygon | protectedplanet.net |
| OpenStreetMap | Port / marina locations | overpass-api.de |

### `ResponsibleAIFooter.tsx`

Always visible at the bottom of every page. Small, unobtrusive.

```
OceanGuard flags vessel detections for human review.
It does not make accusations, identify individuals, or trigger enforcement.
All decisions are made by conservation officers.
```

---

## `vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

---

## `index.html`

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>OceanGuard AI</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  </head>
  <body class="bg-ocean-900 text-white">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## Dockerfile (multi-stage)

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

`nginx.conf`:
```nginx
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://backend:8000/;
    }
}
```

---

## Key Rules

1. The app must work even if the backend returns empty arrays — show empty states, not crashes
2. All backend calls must handle errors — show a user-friendly error message, not a blank screen
3. Leaflet requires its CSS to be imported — add to `index.html` or `main.tsx`
4. `react-leaflet` `<MapContainer>` must have a fixed height (e.g. `h-[500px]`) or the map won't render
5. `riskColor()` helper must be used consistently everywhere a risk level appears (badges, markers, table rows)
6. `ResponsibleAIFooter` must appear on every page — never hide it
7. The Evidence Card "Get AI Explanation" button must be clearly labeled as AI-generated output

---

## Backend API Quick Reference

| Call | What you get |
|---|---|
| `GET /risk-events?source=GFW` | 4 dark-vessel events for the map |
| `GET /risk-events/bar-reef-003` | The headline HIGH-risk event |
| `GET /mpa` | Bar Reef GeoJSON polygon for Leaflet |
| `GET /model-metrics` | mAP50=0.838, 122 detections, training history |
| `POST /agents/narrate` | Body: RiskEvent → `{why_flagged, uncertainty}` |
| `POST /agents/briefing` | Body: RiskEvent[] → `{briefing: string}` |
| `POST /agents/patrol` | Body: RiskEvent[] → ranked list |
| `POST /agents/ask` | Body: `{question}` → `{answer}` |
| `POST /risk-events/{id}/review` | Body: `{review_status}` → updates status |
