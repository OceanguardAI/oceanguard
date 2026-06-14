import React from "react";
import { RiskEvent } from "../types";
import { getRiskColor } from "../lib/riskColor";
import { Search } from "lucide-react";

export default function RiskTable({ events, selected, onSelect }: { 
  events: RiskEvent[];
  selected: RiskEvent | null;
  onSelect: (e: RiskEvent) => void;
}) {
  const [filter, setFilter] = React.useState("ALL");

  const filtered = React.useMemo(() => {
    if (filter === "ALL") return events;
    return events.filter(e => e.risk_level === filter);
  }, [events, filter]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-ocean-700 bg-ocean-800">
        <div className="flex items-center gap-2 text-sm">
          <Search className="w-4 h-4 text-slate-400" />
          <select 
            value={filter} 
            onChange={e => setFilter(e.target.value)}
            className="bg-ocean-900 border border-ocean-700 text-slate-200 rounded px-2 py-1 outline-none focus:border-teal-500"
          >
            <option value="ALL">All Detections</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>
        </div>
        <div className="text-xs text-slate-400">{filtered.length} events</div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase bg-ocean-900/50 text-slate-400 sticky top-0">
            <tr>
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Risk Score</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ocean-700/50">
            {filtered.map(ev => (
              <tr 
                key={ev.id} 
                onClick={() => onSelect(ev)}
                className={`cursor-pointer transition-colors ${selected?.id === ev.id ? 'bg-ocean-700/50' : 'hover:bg-ocean-800'}`}
              >
                <td className="px-4 py-3 font-medium text-slate-200">{ev.id}</td>
                <td className="px-4 py-3 text-slate-400">{new Date(ev.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${getRiskColor(ev.risk_level)}`}>{ev.risk_level}</span>
                    <span className="text-slate-400 text-xs">({ev.risk_score.toFixed(2)})</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    ev.review_status === 'Pending' ? 'bg-slate-700 text-slate-300' :
                    ev.review_status === 'Confirmed Risk' ? 'bg-risk-critical/20 text-risk-critical' :
                    'bg-ocean-900 text-slate-500'
                  }`}>
                    {ev.review_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
