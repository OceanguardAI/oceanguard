import {
  RiskEvent, ModelMetrics, NarrateResponse,
  BriefingResponse, PatrolItem, AskResponse, MPAGeoJSON
} from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";

export interface ActivityAggregate {
  id: string;
  dataset: string;
  lat: number;
  lon: number;
  detection_count: number;
  report_start: string;
  report_end: string;
  provider_time: string | null;
  ingested_at: string;
}

export interface ActivityPage {
  items: ActivityAggregate[];
  total: number;
  offset: number;
  limit: number;
  data_state: "not_loaded" | "available" | "empty" | "stale";
}

export async function fetchIngestStatus(): Promise<{ risk_events_mode: string }> {
  const res = await fetch(`${API_BASE}/ingest/status`);
  if (!res.ok) throw new Error("Failed to fetch source status");
  return res.json();
}

export async function fetchGfwActivity(bbox: [number, number, number, number]): Promise<ActivityPage> {
  const params = new URLSearchParams({ bbox: bbox.join(","), limit: "600" });
  const res = await fetch(`${API_BASE}/activity/gfw?${params}`);
  if (!res.ok) throw new Error("Failed to fetch GFW activity");
  return res.json();
}

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
  spatial_match: boolean;
  verification_status: "acquisition_unverified" | "no_spatial_match";
  provenance: {
    provider: string;
    requested_center: { lat: number; lon: number };
    requested_at: string;
    acquisition_id: string | null;
    observed_at: string | null;
    coverage_status: "scene_metadata_available" | "scene_time_unverified";
    identity_claim: "observation_candidate_only";
  };
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
// not just events in the store. `eventId` is optional comparison context;
// `date` defaults to now for searching an available Sentinel-1 pass.
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

// --- Area sweep: run our model across a whole area (e.g. an MPA) ---
export interface SweepContact {
  lat: number;
  lon: number;
  confidence: number | null;
  status: "new" | "confirmed";
  matched_event_id: string | null;
  nearest_known_km: number | null;
}

export interface SweepResult {
  bbox: [number, number, number, number];
  tiles_scanned: number;
  tiles_failed: number;
  tiles_with_contacts: number;
  effective_tile_deg: number;
  fully_covered: boolean;
  requested_at: string;
  coverage_status: "scene_metadata_available" | "scene_time_unverified";
  tiles_with_scene_metadata: number;
  total_contacts: number;
  new_contacts: number;
  confirmed_contacts: number;
  contacts: SweepContact[];
}

// Sweep an area with the YOLO model on the latest Sentinel-1 pass. bbox is
// [minLon, minLat, maxLon, maxLat]. This can take a while: the area is tiled and
// each tile is a separate Sentinel-1 fetch + inference (the first triggers the
// scale-to-zero service's cold start).
export async function sweepArea(
  bbox: [number, number, number, number],
  date?: string,
): Promise<SweepResult> {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  const params = new URLSearchParams({
    min_lon: String(minLon),
    min_lat: String(minLat),
    max_lon: String(maxLon),
    max_lat: String(maxLat),
    date: date ?? new Date().toISOString(),
  });
  const res = await fetch(`${API_BASE}/verify/yolo/sweep?${params.toString()}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await readError(res, "Area sweep failed"));
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

export async function getBriefing(): Promise<BriefingResponse> {
  const res = await fetch(`${API_BASE}/agents/briefing/current`, { method: "POST" });
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
