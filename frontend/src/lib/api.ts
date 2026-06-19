import {
  RiskEvent, ModelMetrics, NarrateResponse,
  BriefingResponse, PatrolItem, AskResponse, MPAGeoJSON
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";

export async function fetchRiskEvents(source?: string, level?: string): Promise<RiskEvent[]> {
  const params = new URLSearchParams();
  if (source) params.append("source", source);
  if (level) params.append("level", level);
  const q = params.toString();
  const res = await fetch(`${API_BASE}/risk-events${q ? "?" + q : ""}`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function fetchModelMetrics(): Promise<ModelMetrics> {
  const res = await fetch(`${API_BASE}/model-metrics`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

// --- Sentinel-1 SAR image chips ---
let _sarConfigured: boolean | null = null;

export async function sarImageConfigured(): Promise<boolean> {
  if (_sarConfigured !== null) return _sarConfigured;
  try {
    const res = await fetch(`${API_BASE}/sar-image/status`);
    _sarConfigured = res.ok ? Boolean((await res.json()).configured) : false;
  } catch {
    _sarConfigured = false;
  }
  return _sarConfigured;
}

export function sarImageUrl(lat: number, lon: number, date?: string): string {
  const d = date ? `&date=${encodeURIComponent(date)}` : "";
  return `${API_BASE}/sar-image?lat=${lat}&lon=${lon}${d}`;
}

// --- On-demand YOLO verification (our own model on live Sentinel-1) ---
export interface YoloDetection {
  confidence: number;
  bbox_px: [number, number, number, number];
  lat: number;
  lon: number;
}

export interface YoloVerifyResult {
  event_id: string;
  agreement: boolean;
  yolo: {
    found: boolean;
    count: number;
    best_confidence: number;
    detections: YoloDetection[];
    chip_px: number;
    chip_bbox: [number, number, number, number];
    chip_png_b64: string;
    conf_threshold: number;
  };
  updated_event: RiskEvent | null;
}

let _yoloConfigured: boolean | null = null;

export async function yoloVerifyConfigured(): Promise<boolean> {
  if (_yoloConfigured !== null) return _yoloConfigured;
  try {
    const res = await fetch(`${API_BASE}/verify/yolo/status`);
    _yoloConfigured = res.ok ? Boolean((await res.json()).configured) : false;
  } catch {
    _yoloConfigured = false;
  }
  return _yoloConfigured;
}

// Turn any error body into a readable string. FastAPI returns `detail` as a
// string for HTTPExceptions but as an array of objects for 422 validation
// errors — naively throwing that array renders as "[object Object]".
async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    const d = body?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => e?.msg ?? JSON.stringify(e)).join("; ");
    if (d) return typeof d === "object" ? JSON.stringify(d) : String(d);
  } catch {
    /* not JSON */
  }
  return `${fallback} (HTTP ${res.status})`;
}

// Verification runs on the point itself (lat/lon/date), so it works for any
// location an officer picks — an existing detection, an MPA, or open water —
// not just events in the store. `eventId` is optional and only lets the backend
// apply an agreement boost when that detection still exists; `date` defaults to
// now (latest available Sentinel-1 pass).
export async function verifyYolo(point: {
  lat: number; lon: number; date?: string; eventId?: string;
}): Promise<YoloVerifyResult> {
  const params = new URLSearchParams({
    lat: String(point.lat),
    lon: String(point.lon),
    date: point.date ?? new Date().toISOString(),
  });
  if (point.eventId) params.set("event_id", point.eventId);
  const res = await fetch(`${API_BASE}/verify/yolo?${params.toString()}`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(await readError(res, "YOLO verification failed"));
  }
  return res.json();
}

export async function fetchMPA(bbox?: [number, number, number, number]): Promise<MPAGeoJSON> {
  // With a bbox the backend returns only MPAs in that box, so we never pull the
  // full global WDPA set. bbox = [minLon, minLat, maxLon, maxLat].
  const q = bbox ? `?bbox=${bbox.join(",")}` : "";
  const res = await fetch(`${API_BASE}/mpa${q}`);
  if (!res.ok) throw new Error("Failed to fetch MPA");
  return res.json() as Promise<MPAGeoJSON>;
}

export async function updateReviewStatus(id: string, status: string): Promise<RiskEvent> {
  const res = await fetch(`${API_BASE}/risk-events/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ review_status: status })
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

export async function narrateEvent(event: RiskEvent): Promise<NarrateResponse> {
  const res = await fetch(`${API_BASE}/agents/narrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event)
  });
  if (!res.ok) throw new Error("Narrator failed");
  return res.json();
}

export async function getBriefing(events: RiskEvent[]): Promise<BriefingResponse> {
  const res = await fetch(`${API_BASE}/agents/briefing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(events)
  });
  if (!res.ok) throw new Error("Briefing failed");
  return res.json();
}

export async function getPatrolRanking(events: RiskEvent[]): Promise<PatrolItem[]> {
  const res = await fetch(`${API_BASE}/agents/patrol`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(events)
  });
  if (!res.ok) throw new Error("Patrol rank failed");
  return res.json();
}

export async function askOceanGuard(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/agents/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  });
  if (!res.ok) throw new Error("Ask agent failed");
  return res.json();
}
