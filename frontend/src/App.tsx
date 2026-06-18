import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchRiskEvents } from "./lib/api";
import { RiskEvent } from "./types";
import MapView from "./components/MapView";
import EvidenceCard from "./components/EvidenceCard";
import RiskTable from "./components/RiskTable";
import DailyBriefing from "./components/DailyBriefing";
import PatrolBoard from "./components/PatrolBoard";
import AskOceanGuard from "./components/AskOceanGuard";
import ModelMetricsComponent from "./components/ModelMetrics";
import DataSources from "./components/DataSources";
import ResponsibleAIFooter from "./components/ResponsibleAIFooter";
import LandingPage from "./components/LandingPage";
import AnimatedNumber from "./components/ui/AnimatedNumber";
import {
  Activity, BarChart3, Database,
  AlertTriangle, Eye, Layers, Clock,
} from "lucide-react";

type Page = "landing" | "dashboard";
type Tab  = "dashboard" | "metrics" | "sources";

export default function App() {
  const [page, setPage]                 = useState<Page>("landing");
  const [events, setEvents]             = useState<RiskEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<RiskEvent | null>(null);
  const [activeTab, setActiveTab]       = useState<Tab>("dashboard");
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError]   = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEventsLoading(true);
    setEventsError(null);

    fetchRiskEvents()
      .then((data) => {
        if (cancelled) return;
        setEvents(data);
        const highRisk = data.find((e) => e.risk_level === "HIGH" || e.risk_level === "CRITICAL");
        if (highRisk) setSelectedEvent(highRisk);
        else if (data.length > 0) setSelectedEvent(data[0]);
      })
      .catch(() => {
        if (cancelled) return;
        setEvents([]);
        setSelectedEvent(null);
        setEventsError("Couldn't load detections. Check the backend API and refresh.");
      })
      .finally(() => {
        if (!cancelled) setEventsLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  const handleLaunch = () => { setPage("dashboard"); setActiveTab("dashboard"); };

  const handleDemo = () => {
    setPage("dashboard");
    setActiveTab("dashboard");
    const demo =
      events.find((e) => e.id === "bar-reef-003") ||
      events.find((e) => e.risk_level === "CRITICAL") ||
      events.find((e) => e.risk_level === "HIGH");
    if (demo) setSelectedEvent(demo);
  };

  const kpis = [
    { icon: Layers,       label: "Total Detections", value: events.length,                                                                  color: "text-teal-400",    bg: "bg-teal-400/8" },
    { icon: AlertTriangle, label: "High / Critical",  value: events.filter((e) => e.risk_level === "HIGH" || e.risk_level === "CRITICAL").length, color: "text-risk-high",   bg: "bg-risk-high/8" },
    { icon: Eye,          label: "Near MPA",         value: events.filter((e) => e.inside_mpa || e.near_mpa).length,                        color: "text-risk-medium", bg: "bg-risk-medium/8" },
    { icon: Clock,        label: "Pending Review",   value: events.filter((e) => e.review_status === "Pending").length,                     color: "text-slate-300",   bg: "bg-slate-700/25" },
  ];

  if (page === "landing") {
    return <LandingPage onLaunch={handleLaunch} onDemo={handleDemo} />;
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="dashboard"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col h-screen overflow-hidden bg-ocean-950"
      >
        {/* Header */}
        <header className="glass-dark border-b border-ocean-700/40 h-[52px] flex items-center justify-between px-4 shrink-0">
          <button
            onClick={() => setPage("landing")}
            className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
          >
            <img src="/logo.png" alt="OceanGuard AI" className="w-8 h-8 rounded-lg object-cover shadow-lg shadow-teal-500/20" />
            <span className="text-sm font-bold text-white tracking-tight">
              OceanGuard <span className="text-teal-400">AI</span>
              <span className="text-slate-500 font-normal ml-1.5 text-xs">· Sentinel Dashboard</span>
            </span>
          </button>

          <nav className="flex items-center gap-1">
            {([
              { id: "dashboard" as Tab, icon: Activity,  label: "Monitoring"   },
              { id: "metrics"   as Tab, icon: BarChart3,  label: "ML Validation" },
              { id: "sources"   as Tab, icon: Database,   label: "Data Sources"  },
            ]).map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                  activeTab === id
                    ? "bg-teal-400/12 text-teal-400 border border-teal-400/20"
                    : "text-slate-400 hover:text-slate-200 hover:bg-ocean-800/50"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </nav>
        </header>

        {/* KPI Bar */}
        {activeTab === "dashboard" && (
          <div className="shrink-0 flex items-center gap-2.5 px-4 py-2 border-b border-ocean-700/25 bg-ocean-950/80 flex-wrap">
            {kpis.map((kpi) => {
              const Icon = kpi.icon;
              return (
                <div
                  key={kpi.label}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${kpi.bg} border border-ocean-700/30`}
                >
                  <Icon className={`w-3 h-3 ${kpi.color} shrink-0`} />
                  <span className="text-[11px] text-slate-500">{kpi.label}:</span>
                  <span className={`text-sm font-bold ${kpi.color} tabular-nums`}>
                    <AnimatedNumber value={kpi.value} />
                  </span>
                </div>
              );
            })}
            {eventsLoading && (
              <span className="text-[11px] text-slate-600 animate-pulse ml-1">Loading…</span>
            )}
          </div>
        )}

        {/* Main Content */}
        <main className="flex-1 overflow-hidden flex">
          {activeTab === "dashboard" && (
            <>
              {/* Left: Map + Table */}
              <div className="flex-1 flex flex-col min-w-0 border-r border-ocean-700/25">
                {eventsError && events.length === 0 && !eventsLoading ? (
                  <div className="flex-1 flex items-center justify-center p-8">
                    <div className="max-w-sm rounded-2xl border border-risk-high/20 bg-risk-high/5 p-8 text-center space-y-3">
                      <AlertTriangle className="w-8 h-8 text-risk-high mx-auto" />
                      <p className="font-semibold text-white">Backend Offline</p>
                      <p className="text-slate-400 text-sm">{eventsError}</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="h-[58%] border-b border-ocean-700/25 relative">
                      <MapView events={events} selected={selectedEvent} onSelect={setSelectedEvent} />
                    </div>
                    <div className="h-[42%] overflow-hidden">
                      <RiskTable events={events} selected={selectedEvent} onSelect={setSelectedEvent} />
                    </div>
                  </>
                )}
              </div>

              {/* Right: Agents */}
              <div className="w-[440px] shrink-0 flex flex-col overflow-y-auto bg-ocean-950">
                <div className="p-3 space-y-3">
                  <DailyBriefing events={events} />
                  {selectedEvent && (
                    <EvidenceCard
                      event={selectedEvent}
                      onUpdate={(updated) => {
                        setEvents((curr) => curr.map((e) => (e.id === updated.id ? updated : e)));
                        setSelectedEvent((curr) => (curr?.id === updated.id ? updated : curr));
                      }}
                    />
                  )}
                  <PatrolBoard events={events} onSelect={setSelectedEvent} />
                  <AskOceanGuard />
                </div>
              </div>
            </>
          )}

          {activeTab === "metrics" && (
            <motion.div
              key="metrics"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex-1 overflow-y-auto p-8"
            >
              <ModelMetricsComponent />
            </motion.div>
          )}

          {activeTab === "sources" && (
            <motion.div
              key="sources"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="flex-1 overflow-y-auto p-8"
            >
              <DataSources />
            </motion.div>
          )}
        </main>

        <ResponsibleAIFooter />
      </motion.div>
    </AnimatePresence>
  );
}
