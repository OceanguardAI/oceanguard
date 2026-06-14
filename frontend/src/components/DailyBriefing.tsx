import React, { useEffect, useState } from "react";
import { RiskEvent } from "../types";
import { getBriefing } from "../lib/api";
import { FileText } from "lucide-react";

export default function DailyBriefing({ events }: { events: RiskEvent[] }) {
  const [briefing, setBriefing] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (events.length === 0) return;
    setLoading(true);
    getBriefing(events)
      .then(res => setBriefing(res.briefing))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [events]);

  if (!loading && !briefing) return null;

  return (
    <div className="bg-ocean-800 border border-ocean-700 rounded-lg p-4 shadow-lg">
      <h3 className="text-xs font-semibold text-teal-400 uppercase tracking-wider mb-3 flex items-center gap-2">
        <FileText className="w-4 h-4" /> Daily Briefing
      </h3>
      {loading ? (
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-3 py-1">
            <div className="h-2 bg-ocean-700 rounded w-3/4"></div>
            <div className="h-2 bg-ocean-700 rounded w-full"></div>
            <div className="h-2 bg-ocean-700 rounded w-5/6"></div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-300 leading-relaxed">
          {briefing}
        </p>
      )}
    </div>
  );
}
