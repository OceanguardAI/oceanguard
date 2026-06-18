import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { RiskEvent } from "../types";
import { getBriefing } from "../lib/api";
import { FileText, Loader2, AlertCircle, RefreshCw } from "lucide-react";

export default function DailyBriefing({ events }: { events: RiskEvent[] }) {
  const [briefing, setBriefing] = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const requestKey = events
    .map((e) => `${e.id}:${e.risk_score}:${e.risk_level}:${e.distance_to_mpa_km ?? "na"}:${e.inside_mpa ? 1 : 0}:${e.near_mpa ? 1 : 0}`)
    .join("|");

  const load = (key: string) => {
    if (events.length === 0) { setBriefing(null); setError(null); return; }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getBriefing(events)
      .then((res) => { if (!cancelled) setBriefing(res.briefing); })
      .catch(() => { if (!cancelled) { setBriefing(null); setError("Couldn't load the daily briefing."); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  };

  useEffect(() => {
    const cleanup = load(requestKey);
    return cleanup;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  if (!loading && !briefing && !error) return null;

  return (
    <div className="rounded-xl border border-ocean-700/60 bg-ocean-800/50 backdrop-blur-sm overflow-hidden shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ocean-700/40">
        <div className="flex items-center gap-2">
          <FileText className="w-3.5 h-3.5 text-teal-400" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-teal-400">
            Executive Briefing
          </span>
        </div>
        {!loading && error && (
          <button
            onClick={() => load(requestKey)}
            className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-teal-400 transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        )}
      </div>

      <div className="p-4">
        <AnimatePresence mode="wait">
          {loading && (
            <motion.div key="loading"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="space-y-2.5 py-1"
            >
              {[3, 4, 3].map((w, i) => (
                <div key={i} className={`h-2 bg-ocean-700/60 rounded-full animate-pulse`}
                  style={{ width: `${w * 25}%` }} />
              ))}
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

          {!loading && briefing && (
            <motion.div key="briefing"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              {/* Loader indicator */}
              <div className="flex items-center gap-1.5 mb-2.5">
                <Loader2 className="w-2.5 h-2.5 text-teal-400 opacity-0" />
                <span className="text-[10px] text-slate-500">AI-generated · {new Date().toLocaleDateString()}</span>
              </div>
              <p className="text-xs text-slate-300 leading-[1.8] whitespace-pre-wrap">{briefing}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
