import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RiskEvent } from "../types";
import { getRiskBgColor } from "../lib/riskColor";
import { narrateEvent, updateReviewStatus } from "../lib/api";
import {
  Navigation2, Activity, Map, Clock,
  CheckCircle, XCircle, Loader2, AlertCircle,
  Anchor, Shield, Info,
} from "lucide-react";
import RiskBadge from "./ui/RiskBadge";
import GradientButton from "./ui/GradientButton";

interface EvidenceCardProps {
  event: RiskEvent;
  onUpdate: (e: RiskEvent) => void;
}

/** SVG ring showing risk score 0-100 */
function RiskRing({ score, level }: { score: number; level: string }) {
  const pct     = Math.min(Math.max(score * 100, 0), 100);
  const r       = 26;
  const circ    = 2 * Math.PI * r;
  const dash    = circ * (pct / 100);

  const strokeColor: Record<string, string> = {
    LOW:      "#22c55e",
    MEDIUM:   "#fbbf24",
    HIGH:     "#f97316",
    CRITICAL: "#dc2626",
  };
  const color = strokeColor[level?.toUpperCase() ?? "LOW"] ?? "#94a3b8";

  return (
    <div className="relative flex items-center justify-center w-16 h-16 shrink-0">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 64 64" width="64" height="64">
        <circle cx="32" cy="32" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        <circle
          cx="32" cy="32" r={r} fill="none"
          stroke={color} strokeWidth="5"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 4px ${color}80)` }}
        />
      </svg>
      <span className="text-xs font-extrabold text-white z-10">{pct.toFixed(0)}</span>
    </div>
  );
}

function FieldRow({ label, icon, value }: { label: string; icon: React.ReactNode; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        <span className="text-slate-600">{icon}</span>{label}
      </div>
      <div className="text-sm text-slate-200 font-medium">{value}</div>
    </div>
  );
}

export default function EvidenceCard({ event, onUpdate }: EvidenceCardProps) {
  const [narrative, setNarrative] = useState<{ why_flagged: string; uncertainty: string } | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setNarrative(null);
    setError(null);
    setLoading(true);

    narrateEvent(event)
      .then((res) => { if (!cancelled) setNarrative(res); })
      .catch(() => { if (!cancelled) setError("AI explanation unavailable. Check the backend."); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [event.id]);

  const handleReview = async (status: string) => {
    try {
      setReviewError(null);
      const updated = await updateReviewStatus(event.id, status);
      onUpdate(updated);
    } catch {
      setReviewError("Could not update review status. Try again.");
    }
  };

  const aisLabel =
    event.ais_matched
      ? { text: "Matched", className: "text-risk-low" }
      : event.ais_data_available
      ? { text: "Dark (No AIS Match)", className: "text-risk-critical" }
      : { text: "No Coverage", className: "text-slate-400" };

  // Source tags
  const tags = [
    "SAR · Sentinel-1",
    event.ais_data_available ? "AIS · GFW" : null,
    event.inside_mpa || event.near_mpa ? "MPA · WDPA" : null,
  ].filter(Boolean) as string[];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-xl border border-ocean-700/60 bg-ocean-800/60 backdrop-blur-sm overflow-hidden shadow-xl"
    >
      {/* Header */}
      <div className="p-4 border-b border-ocean-700/40 flex items-center gap-3">
        <RiskRing score={event.risk_score} level={event.risk_level} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h2 className="text-sm font-bold text-white truncate">Detection {event.id}</h2>
            <RiskBadge level={event.risk_level} score={event.risk_score} size="xs" />
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <Clock className="w-3 h-3" />
            {new Date(event.timestamp).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })}
          </div>
        </div>
      </div>

      {/* Source tags */}
      <div className="px-4 py-2 border-b border-ocean-700/30 flex items-center gap-2 flex-wrap">
        {tags.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-ocean-700/40 border border-ocean-600/30 text-[10px] text-slate-400 font-medium">
            {t}
          </span>
        ))}
      </div>

      {/* Fields grid */}
      <div className="p-4 grid grid-cols-2 gap-4 border-b border-ocean-700/30 bg-ocean-900/20">
        <FieldRow
          label="Location"
          icon={<Map className="w-2.5 h-2.5" />}
          value={`${event.lat.toFixed(4)}°N, ${event.lon.toFixed(4)}°E`}
        />
        <FieldRow
          label="MPA Proximity"
          icon={<Navigation2 className="w-2.5 h-2.5" />}
          value={
            event.inside_mpa ? (
              <span className="text-risk-critical font-semibold">Inside MPA</span>
            ) : event.near_mpa ? (
              <span className="text-risk-high font-semibold">{event.distance_to_mpa_km} km from MPA</span>
            ) : (
              <span className="text-slate-400">Outside protected zones</span>
            )
          }
        />
        <FieldRow
          label="AIS Status"
          icon={<Activity className="w-2.5 h-2.5" />}
          value={<span className={aisLabel.className}>{aisLabel.text}</span>}
        />
        <FieldRow
          label="SAR Confidence"
          icon={<Anchor className="w-2.5 h-2.5" />}
          value={`${(event.sar_confidence * 100).toFixed(1)}% · ${event.image_quality}`}
        />
        {event.recommended_action && (
          <div className="col-span-2">
            <FieldRow
              label="Recommended Action"
              icon={<Shield className="w-2.5 h-2.5" />}
              value={<span className="text-teal-300">{event.recommended_action}</span>}
            />
          </div>
        )}
      </div>

      {/* AI Analysis */}
      <div className="p-4 border-b border-ocean-700/30">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse shrink-0" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-teal-400">AI Agent Analysis</span>
        </div>

        <AnimatePresence mode="wait">
          {loading && (
            <motion.div key="loading"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 text-xs text-slate-400 py-2"
            >
              <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
              Agent is analysing detection context…
            </motion.div>
          )}

          {!loading && error && (
            <motion.div key="error"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-start gap-2 text-xs text-risk-high bg-risk-high/8 border border-risk-high/20 rounded-lg p-3"
            >
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {error}
            </motion.div>
          )}

          {!loading && narrative && (
            <motion.div key="narrative"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
              className="space-y-3 text-xs leading-relaxed"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-slate-400 font-semibold">
                  <Info className="w-3 h-3" /> Why Flagged
                </div>
                <p className="text-slate-300">{narrative.why_flagged}</p>
              </div>
              <div className="space-y-1 border-t border-ocean-700/30 pt-3">
                <div className="text-slate-500 font-semibold">Uncertainty</div>
                <p className="text-slate-400">{narrative.uncertainty}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Review Actions */}
      <div className="p-4 bg-ocean-900/30">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="text-xs text-slate-500">
            Status:&nbsp;
            <span className={`font-semibold ${event.review_status === "Confirmed Risk" ? "text-risk-critical" : event.review_status === "False Positive" ? "text-slate-400" : "text-slate-300"}`}>
              {event.review_status}
            </span>
          </div>
          {event.review_status === "Pending" && (
            <div className="flex gap-2">
              <GradientButton variant="ghost" size="xs" onClick={() => handleReview("False Positive")}>
                <XCircle className="w-3 h-3" /> False Positive
              </GradientButton>
              <GradientButton variant="primary" size="xs" onClick={() => handleReview("Confirmed Risk")}>
                <CheckCircle className="w-3 h-3" /> Confirm Risk
              </GradientButton>
            </div>
          )}
        </div>
        {reviewError && (
          <p className="mt-2 text-[11px] text-risk-high">{reviewError}</p>
        )}
      </div>
    </motion.div>
  );
}
