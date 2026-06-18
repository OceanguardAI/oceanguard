export interface RiskEvent {
  id: string;
  source: string;
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
  training_history: Array<{
    epoch: number;
    map50: number;
    loss: number;
  }>;
}

export interface NarrateResponse {
  why_flagged: string;
  uncertainty: string;
}

export interface BriefingResponse {
  briefing: string;
}

export interface PatrolItem {
  id: string;
  rank: number;
  risk_level: string;
  distance_to_mpa_km: number | null;
  justification: string;
}

export interface AskResponse {
  answer: string;
}

export type GeoJSONPosition = [number, number];

export interface GeoJSONPolygonGeometry {
  type: "Polygon";
  coordinates: GeoJSONPosition[][];
}

export interface GeoJSONMultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: GeoJSONPosition[][][];
}

export type GeoJSONGeometry = GeoJSONPolygonGeometry | GeoJSONMultiPolygonGeometry;

export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSONGeometry;
  properties?: Record<string, unknown>;
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

export type MPAGeoJSON = GeoJSONFeature | GeoJSONFeatureCollection;
