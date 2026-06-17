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

export async function fetchMPA(): Promise<MPAGeoJSON> {
  const res = await fetch(`${API_BASE}/mpa`);
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
