import React, { useEffect, useState } from "react";
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
import { ShieldAlert, Activity, BarChart3, Database } from "lucide-react";

export default function App() {
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<RiskEvent | null>(null);
  const [activeTab, setActiveTab] = useState<"dashboard" | "metrics" | "sources">("dashboard");
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);

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
        setEventsError("Couldn't load detections. Check the backend API and refresh the page.");
      })
      .finally(() => {
        if (!cancelled) setEventsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="bg-ocean-800 border-b border-ocean-700 h-16 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-3">
          <ShieldAlert className="w-8 h-8 text-teal-400" />
          <h1 className="text-xl font-bold tracking-wide">
            OceanGuard AI <span className="text-slate-400 font-normal">| Sentinel Dashboard</span>
          </h1>
        </div>
        <nav className="flex gap-4">
          <button 
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${activeTab === "dashboard" ? "bg-ocean-700 text-white" : "text-slate-400 hover:bg-ocean-800 hover:text-slate-200"}`}
          >
            <Activity className="w-4 h-4" /> Monitoring
          </button>
          <button 
            onClick={() => setActiveTab("metrics")}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${activeTab === "metrics" ? "bg-ocean-700 text-white" : "text-slate-400 hover:bg-ocean-800 hover:text-slate-200"}`}
          >
            <BarChart3 className="w-4 h-4" /> ML Validation
          </button>
          <button 
            onClick={() => setActiveTab("sources")}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${activeTab === "sources" ? "bg-ocean-700 text-white" : "text-slate-400 hover:bg-ocean-800 hover:text-slate-200"}`}
          >
            <Database className="w-4 h-4" /> Data Sources
          </button>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden flex bg-ocean-900">
        {activeTab === "dashboard" && (
          <>
            {/* Left Column: Map & Table */}
            <div className="flex-1 flex flex-col min-w-0 border-r border-ocean-700">
              {eventsError && events.length === 0 && !eventsLoading ? (
                <div className="flex-1 flex items-center justify-center p-8">
                  <div className="max-w-md rounded-lg border border-risk-high/30 bg-risk-high/10 p-5 text-sm text-slate-200">
                    {eventsError}
                  </div>
                </div>
              ) : (
                <>
                  <div className="h-[55%] border-b border-ocean-700 relative">
                    <MapView events={events} selected={selectedEvent} onSelect={setSelectedEvent} />
                  </div>
                  <div className="h-[45%] overflow-hidden bg-ocean-800/50">
                    <RiskTable events={events} selected={selectedEvent} onSelect={setSelectedEvent} />
                  </div>
                </>
              )}
            </div>

            {/* Right Column: Agents & Details */}
            <div className="w-[450px] shrink-0 flex flex-col overflow-y-auto bg-ocean-900">
              <div className="p-4 space-y-4">
                <DailyBriefing events={events} />
                {selectedEvent && (
                  <EvidenceCard event={selectedEvent} onUpdate={(updated) => {
                    setEvents((current) => current.map((event) => event.id === updated.id ? updated : event));
                    setSelectedEvent((current) => current?.id === updated.id ? updated : current);
                  }} />
                )}
                <PatrolBoard events={events} onSelect={setSelectedEvent} />
                <AskOceanGuard />
              </div>
            </div>
          </>
        )}

        {activeTab === "metrics" && (
          <div className="flex-1 overflow-y-auto p-8">
            <ModelMetricsComponent />
          </div>
        )}

        {activeTab === "sources" && (
          <div className="flex-1 overflow-y-auto p-8">
            <DataSources />
          </div>
        )}
      </main>

      <ResponsibleAIFooter />
    </div>
  );
}
