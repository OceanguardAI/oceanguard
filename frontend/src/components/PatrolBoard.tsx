import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RiskEvent, PatrolItem } from "../types";
import { getPatrolRanking } from "../lib/api";
import { getRiskColor } from "../lib/riskColor";
import { Crosshair, Loader2, AlertCircle, ChevronRight } from "lucide-react";
import RiskBadge from "./ui/RiskBadge";

const RANK_STYLES = [
  "from-risk-critical/20 border-risk-critical/30 shadow-risk-critical/10",
  "from-risk-high/15 border-risk-high/20 shadow-risk-high/5",
  "from-ocean-700/30 border-ocean-600/30 shadow-ocean-700/5",
];

const RANK_LABELS = ["#1", "#2", "#3"];

export default function PatrolBoard({
  events,
  onSelect,
}: {
  events: RiskEvent[];
  onSelect: (e: RiskEvent) => void;
}) {
  const [items, setItems]   = useState<PatrolItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);

  const requestKey = events
    .map((e) => `${e.id}:${e.risk_score}:${e.risk_level}:${e.distance_to_mpa_km ?? "na"}:${e.inside_mpa ? 1 : 0}:${e.near_mpa ? 1 : 0}`)
    .join("|");

  useEffect(() => {
    if (events.length === 0) { setItems([]); setError(null); return; }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getPatrolRanking(events)
      .then((res) => { if (!cancelled) setItems(res.slice(0, 3)); })
      .catch(() => { if (!cancelled) { setItems([]); setError("Couldn't load patrol priorities."); } })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  if (!loading && items.length === 0 && !error) return null;

  return (
    <div className="rounded-xl border border-ocean-700/60 bg-ocean-800/50 backdrop-blur-sm overflow-hidden shadow-lg">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-ocean-700/40">
        <Crosshair className="w-3.5 h-3.5 text-teal-400" />
        <span className="text-[10px] font-semibold uppercase tracking-widest text-teal-400">Recommended Patrols</span>
      </div>

      <div className="p-3 space-y-2">
        {loading && (
          <div className="flex items-center gap-2 text-xs text-slate-400 py-3 justify-center">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
            Generating patrol priorities…
          </div>
        )}

        {!loading && error && (
          <div className="flex items-center gap-2 text-xs text-risk-high bg-risk-high/8 border border-risk-high/20 rounded-lg p-3">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
          </div>
        )}

        <AnimatePresence>
          {!loading && items.map((item, i) => (
            <motion.button
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25, delay: i * 0.07 }}
              onClick={() => { const ev = events.find((e) => e.id === item.id); if (ev) onSelect(ev); }}
              className={`w-full text-left rounded-xl border bg-gradient-to-r to-transparent p-3 transition-all duration-200 hover:border-teal-400/25 hover:shadow-md group ${RANK_STYLES[i] ?? RANK_STYLES[2]}`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-extrabold text-slate-300 w-6 shrink-0">{RANK_LABELS[i]}</span>
                  <span className="text-sm font-bold text-white truncate">{item.id}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <RiskBadge level={item.risk_level} size="xs" />
                  <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-teal-400 transition-colors" />
                </div>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-8">{item.justification}</p>
              {item.distance_to_mpa_km !== null && (
                <p className="text-[10px] text-slate-500 pl-8 mt-1">{item.distance_to_mpa_km} km from MPA</p>
              )}
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
