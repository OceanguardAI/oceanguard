import React from "react";
import { RiskEvent } from "../types";
import { getRiskColor } from "../lib/riskColor";
import { Search, ChevronUp, ChevronDown } from "lucide-react";
import RiskBadge from "./ui/RiskBadge";

const STATUS_STYLE: Record<string, string> = {
  "Pending":        "bg-slate-700/40 text-slate-400 border-slate-700/50",
  "Confirmed Risk": "bg-risk-critical/10 text-risk-critical border-risk-critical/20",
  "False Positive": "bg-ocean-700/30 text-slate-500 border-ocean-700/40",
  "Resolved":       "bg-risk-low/10 text-risk-low border-risk-low/20",
};

export default function RiskTable({
  events,
  selected,
  onSelect,
}: {
  events: RiskEvent[];
  selected: RiskEvent | null;
  onSelect: (e: RiskEvent) => void;
}) {
  const [filter, setFilter] = React.useState("ALL");

  const filtered = React.useMemo(() => {
    if (filter === "ALL") return events;
    return events.filter((e) => e.risk_level === filter);
  }, [events, filter]);

  return (
    <div className="flex flex-col h-full bg-ocean-950/60">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-ocean-700/25 bg-ocean-900/30 shrink-0">
        <div className="flex items-center gap-2">
          <Search className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-ocean-900/60 border border-ocean-700/50 text-slate-300 rounded-lg px-2.5 py-1 text-xs outline-none focus:border-teal-400/40 transition-colors"
          >
            <option value="ALL">All Detections</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>
        </div>
        <span className="text-[11px] text-slate-600">{filtered.length} events</span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs text-left">
          <thead className="sticky top-0 z-10 bg-ocean-950/90 backdrop-blur-sm border-b border-ocean-700/25">
            <tr>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">ID</th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Time</th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Risk</th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">MPA</th>
              <th className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((ev) => {
              const isSelected = selected?.id === ev.id;
              return (
                <tr
                  key={ev.id}
                  onClick={() => onSelect(ev)}
                  className={`cursor-pointer border-b border-ocean-700/20 transition-colors duration-100 ${
                    isSelected
                      ? "bg-teal-400/6 border-l-2 border-l-teal-400"
                      : "hover:bg-ocean-800/40"
                  }`}
                >
                  <td className={`px-4 py-2.5 font-semibold ${isSelected ? "text-teal-300" : "text-slate-200"}`}>
                    {ev.id}
                  </td>
                  <td className="px-4 py-2.5 text-slate-500 tabular-nums">
                    {new Date(ev.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-4 py-2.5">
                    <RiskBadge level={ev.risk_level} score={ev.risk_score} size="xs" />
                  </td>
                  <td className="px-4 py-2.5">
                    {ev.inside_mpa ? (
                      <span className="text-[10px] font-semibold text-risk-critical">Inside</span>
                    ) : ev.near_mpa ? (
                      <span className="text-[10px] font-semibold text-risk-high">{ev.distance_to_mpa_km} km</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold border ${STATUS_STYLE[ev.review_status] ?? "bg-slate-800 text-slate-400"}`}>
                      {ev.review_status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="flex items-center justify-center py-12 text-slate-600 text-sm">
            No detections match the current filter.
          </div>
        )}
      </div>
    </div>
  );
}
