import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Database, Satellite, Map, ShieldAlert, ExternalLink } from "lucide-react";
import { fetchSourceHealth, SourceHealthResponse } from "../lib/api";

const SOURCES = [
  {
    icon: Satellite,
    title: "Synthetic Aperture Radar (SAR)",
    desc: "SAR satellites beam microwaves to Earth and measure the reflection. Metal vessels appear as bright pixels — visible through clouds and at night.",
    tags: ["Sentinel-1", "xView3 Dataset"],
    trust: "High",
    color: "teal",
  },
  {
    icon: Database,
    title: "Automatic Identification System (AIS)",
    desc: "Ships broadcast their location via AIS to avoid collisions. OceanGuard correlates SAR detections with AIS signals — no match means the vessel is \"dark\".",
    tags: ["Global Fishing Watch"],
    trust: "High",
    color: "teal",
  },
  {
    icon: Map,
    title: "Marine Protected Areas (MPA)",
    desc: "Geospatial boundaries of protected marine zones. Detections inside or within 5 km receive significantly higher risk scores.",
    tags: ["ProtectedPlanet", "WDPA", "IUCN"],
    trust: "High",
    color: "teal",
  },
  {
    icon: ShieldAlert,
    title: "Coastal Infrastructure",
    desc: "Locations of ports, marinas, and platforms. Used to contextualise vessel behaviour — loitering near ports may just be queue behaviour.",
    tags: ["OpenStreetMap", "Overpass API"],
    trust: "Medium",
    color: "amber",
  },
];

const TRUST_COLOR: Record<string, string> = {
  High:   "bg-risk-low/10 text-risk-low border-risk-low/20",
  Medium: "bg-risk-medium/10 text-risk-medium border-risk-medium/20",
  Low:    "bg-risk-high/10 text-risk-high border-risk-high/20",
};

export default function DataSources() {
  const [health, setHealth] = useState<SourceHealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchSourceHealth()
      .then((result) => { if (!cancelled) setHealth(result); })
      .catch(() => { if (!cancelled) setHealthError(true); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      <div>
        <h2 className="text-2xl font-extrabold text-white mb-1">Data Sources &amp; Provenance</h2>
        <p className="text-slate-400 text-sm">OceanGuard separates satellite activity, observation candidates, AIS association, protected areas, and review cases. A source status is not the same as proof that a vessel was observed.</p>
      </div>

      <div className="rounded-xl border border-ocean-700/60 bg-ocean-800/45 p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="text-xs font-bold text-teal-400 uppercase tracking-widest">Live Source Readiness</h3>
            <p className="text-[11px] text-slate-500 mt-1">Configured means credentials exist; it does not guarantee current coverage.</p>
          </div>
          {health && <span className="text-[10px] text-slate-600">Updated {new Date(health.generated_at).toLocaleTimeString()}</span>}
        </div>
        {healthError && <p className="text-xs text-risk-high">Source health is unavailable.</p>}
        {!health && !healthError && <p className="text-xs text-slate-500">Checking provider readiness...</p>}
        {health && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {health.sources.map((source) => (
              <div key={source.id} className="rounded-lg border border-ocean-700/50 bg-ocean-900/40 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-slate-200">{source.id}</span>
                  <span className={`text-[10px] uppercase tracking-wider ${source.configured ? "text-risk-low" : "text-slate-500"}`}>
                    {source.configured ? source.data_state : "not configured"}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">{source.limitation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {SOURCES.map((src, i) => {
          const Icon = src.icon;
          return (
            <motion.div
              key={src.title}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.38, delay: i * 0.08 }}
              className="rounded-xl border border-ocean-700/60 bg-ocean-800/50 backdrop-blur-sm p-6 flex flex-col gap-4 hover:border-teal-400/20 transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="w-10 h-10 rounded-xl bg-teal-400/8 border border-teal-400/15 flex items-center justify-center shrink-0">
                  <Icon className="w-5 h-5 text-teal-400" />
                </div>
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${TRUST_COLOR[src.trust] ?? ""}`}>
                  {src.trust} Trust
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-white mb-2">{src.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{src.desc}</p>
              </div>

              <div className="flex items-center gap-2 flex-wrap mt-auto">
                {src.tags.map((tag) => (
                  <span key={tag} className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-500 bg-ocean-700/30 border border-ocean-700/40 rounded-md px-2 py-0.5">
                    <ExternalLink className="w-2.5 h-2.5" /> {tag}
                  </span>
                ))}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Data pipeline note */}
      <div className="rounded-xl border border-teal-400/10 bg-teal-400/3 p-5">
        <h3 className="text-xs font-bold text-teal-400 uppercase tracking-widest mb-2">Data Pipeline</h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          SAR evidence and model verification are requested on demand when the provider is configured. GFW activity,
          AIS samples, and durable operational observations are separate records. The dashboard labels source health and
          uncertainty so a missing provider response is not presented as a vessel absence.
        </p>
      </div>
    </div>
  );
}
