import React, { useEffect, useState } from "react";
import { RiskEvent, PatrolItem } from "../types";
import { getPatrolRanking } from "../lib/api";
import { getRiskColor } from "../lib/riskColor";
import { Crosshair } from "lucide-react";

export default function PatrolBoard({ events, onSelect }: { events: RiskEvent[]; onSelect: (e: RiskEvent) => void }) {
  const [items, setItems] = useState<PatrolItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestKey = events
    .map(
      (event) =>
        `${event.id}:${event.risk_score}:${event.risk_level}:${event.distance_to_mpa_km ?? "na"}:${event.inside_mpa ? 1 : 0}:${event.near_mpa ? 1 : 0}`
    )
    .join("|");

  useEffect(() => {
    if (events.length === 0) {
      setItems([]);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    getPatrolRanking(events)
      .then((res) => {
        if (!cancelled) setItems(res.slice(0, 3));
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setError("Couldn't load patrol priorities. Try again.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [requestKey]);

  if (!loading && items.length === 0 && !error) return null;

  return (
    <div className="bg-ocean-800 border border-ocean-700 rounded-lg p-4 shadow-lg">
      <h3 className="text-xs font-semibold text-teal-400 uppercase tracking-wider mb-3 flex items-center gap-2">
        <Crosshair className="w-4 h-4" /> Recommended Patrols
      </h3>
      
      {loading ? (
        <div className="text-sm text-slate-400 animate-pulse">Generating patrol priorities...</div>
      ) : error ? (
        <div className="text-sm text-risk-high">{error}</div>
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <div 
              key={item.id} 
              className="bg-ocean-900 border border-ocean-700 p-3 rounded cursor-pointer hover:border-teal-500/50 transition-colors"
              onClick={() => {
                const ev = events.find(e => e.id === item.id);
                if (ev) onSelect(ev);
              }}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-bold text-slate-200">#{item.rank} {item.id}</span>
                <span className={`text-xs font-bold ${getRiskColor(item.risk_level)}`}>{item.risk_level}</span>
              </div>
              <p className="text-xs text-slate-400">{item.justification}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
