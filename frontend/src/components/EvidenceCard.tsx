import React, { useState, useEffect } from "react";
import { RiskEvent } from "../types";
import { getRiskBgColor, getRiskColor } from "../lib/riskColor";
import { narrateEvent, updateReviewStatus } from "../lib/api";
import { Navigation2, Activity, Map, Clock, CheckCircle, XCircle } from "lucide-react";

export default function EvidenceCard({ event, onUpdate }: { event: RiskEvent; onUpdate: (e: RiskEvent) => void }) {
  const [narrative, setNarrative] = useState<{why_flagged: string, uncertainty: string} | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    narrateEvent(event)
      .then(res => setNarrative(res))
      .finally(() => setLoading(false));
  }, [event.id]);

  const handleReview = async (status: string) => {
    try {
      const updated = await updateReviewStatus(event.id, status);
      onUpdate(updated);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="bg-ocean-800 border border-ocean-700 rounded-lg overflow-hidden shadow-lg">
      <div className="p-4 border-b border-ocean-700 flex justify-between items-start">
        <div>
          <h2 className="text-lg font-bold text-white mb-1">Detection {event.id}</h2>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Clock className="w-3 h-3" /> {new Date(event.timestamp).toLocaleString()}
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${getRiskBgColor(event.risk_level)}`}>
          {event.risk_level} ({(event.risk_score * 100).toFixed(0)})
        </div>
      </div>

      <div className="p-4 grid grid-cols-2 gap-4 text-sm border-b border-ocean-700 bg-ocean-900/30">
        <div>
          <div className="text-slate-500 mb-1 flex items-center gap-1"><Map className="w-3 h-3"/> Location</div>
          <div className="text-slate-200">{event.lat.toFixed(4)}N, {event.lon.toFixed(4)}E</div>
        </div>
        <div>
          <div className="text-slate-500 mb-1 flex items-center gap-1"><Navigation2 className="w-3 h-3"/> Proximity</div>
          <div className="text-slate-200">
            {event.near_mpa ? <span className="text-risk-high font-medium">{event.distance_to_mpa_km}km from MPA</span> : "Outside protected zones"}
          </div>
        </div>
        <div>
          <div className="text-slate-500 mb-1 flex items-center gap-1"><Activity className="w-3 h-3"/> AIS Status</div>
          <div className="text-slate-200">
            {event.ais_matched ? "Matched" : (event.ais_data_available ? "Unmatched (Dark)" : "No Coverage")}
          </div>
        </div>
        <div>
          <div className="text-slate-500 mb-1">SAR Confidence</div>
          <div className="text-slate-200">{(event.sar_confidence * 100).toFixed(1)}% ({event.image_quality})</div>
        </div>
      </div>

      <div className="p-4">
        <h3 className="text-xs font-semibold text-teal-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
          AI Agent Analysis
        </h3>
        {loading ? (
          <div className="text-sm text-slate-400 animate-pulse">Agent is analysing detection context...</div>
        ) : narrative ? (
          <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
            <p><strong className="text-slate-200">Why flagged:</strong> {narrative.why_flagged}</p>
            <p className="text-slate-400"><strong className="text-slate-300">Uncertainty:</strong> {narrative.uncertainty}</p>
          </div>
        ) : null}
      </div>

      <div className="p-4 bg-ocean-900/50 border-t border-ocean-700">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Status: <span className="text-slate-200 font-medium">{event.review_status}</span></span>
          {event.review_status === "Pending" && (
            <div className="flex gap-2">
              <button 
                onClick={() => handleReview("False Positive")}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-300 bg-ocean-700 hover:bg-ocean-600 rounded transition-colors"
              >
                <XCircle className="w-3 h-3" /> False Positive
              </button>
              <button 
                onClick={() => handleReview("Confirmed Risk")}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-500 rounded transition-colors"
              >
                <CheckCircle className="w-3 h-3" /> Confirm Risk
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
