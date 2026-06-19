import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchRiskEvents, verifyYolo, yoloVerifyConfigured, YoloVerifyResult } from "./lib/api";
import { RiskEvent } from "./types";
import MapView from "./components/MapView";
import EvidenceCard from "./components/EvidenceCard";
import YoloResultView from "./components/YoloResultView";
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
  List, FileText, Crosshair, MessageSquare, X,
  Radar, ScanSearch, Loader2, AlertCircle,
} from "lucide-react";

type Page      = "landing" | "dashboard";
type Tab       = "dashboard" | "metrics" | "sources";
type LeftPanel = "detections" | "briefing" | "patrols" | null;

const RISK_DOT: Record<string, string> = {
  CRITICAL: "#dc2626", HIGH: "#f97316", MEDIUM: "#fbbf24", LOW: "#22c55e",
};

/** A glass panel floating over the map. Components inside bring their own card
 *  chrome, so this just positions, frames, scrolls, and adds a close button. */
function Floating({
  className, onClose, framed, scroll = true, children,
}: {
  className: string;
  onClose?: () => void;
  framed?: boolean;
  scroll?: boolean;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
      className={`pointer-events-auto absolute ${className}`}
    >
      {onClose && (
        <button
          onClick={onClose}
          aria-label="Close panel"
          className="absolute -top-2.5 -right-2.5 z-20 w-6 h-6 rounded-full bg-ocean-800 border border-ocean-600 text-slate-400 hover:text-white hover:border-teal-400/40 flex items-center justify-center shadow-lg transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      )}
      <div
        className={`h-full ${scroll ? "overflow-y-auto" : "overflow-hidden"} ${
          framed ? "rounded-xl border border-ocean-700/60 bg-ocean-900/95 backdrop-blur-md shadow-2xl" : ""
        }`}
      >
        {children}
      </div>
    </motion.div>
  );
}

/** Right-side panel for an on-demand area scan: runs the YOLO model on the live
 *  Sentinel-1 radar at a point the officer clicked, anywhere on the map. */
function ScanPanel({
  point, loading, error, result,
}: {
  point: { lat: number; lon: number };
  loading: boolean;
  error: string | null;
  result: YoloVerifyResult | null;
}) {
  return (
    <div className="rounded-xl border border-cyan-700/40 bg-ocean-800/60 backdrop-blur-sm overflow-hidden shadow-xl">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-ocean-700/40">
        <div className="w-5 h-5 rounded-md bg-gradient-to-br from-cyan-500 to-cyan-400 flex items-center justify-center">
          <Radar className="w-3 h-3 text-white" />
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-cyan-300">Area Radar Scan</span>
        <span className="ml-auto text-[10px] text-slate-500 tabular-nums">
          {point.lat.toFixed(4)}°, {point.lon.toFixed(4)}°
        </span>
      </div>

      <div className="p-4">
        <p className="text-[11px] text-slate-500 leading-relaxed mb-3">
          Running our ship-detection model on the latest Sentinel-1 radar pass for this point —
          independent of AIS, so it catches dark vessels anywhere you look.
        </p>

        {loading && (
          <div className="flex items-center gap-2 text-xs text-cyan-300 py-3">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Scanning radar… (first scan can take ~1 min)
          </div>
        )}

        {!loading && error && (
          <div className="flex items-start gap-2 text-xs text-risk-high bg-risk-high/8 border border-risk-high/20 rounded-lg p-3">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {error}
          </div>
        )}

        {!loading && result && (
          <YoloResultView result={result} label={`${point.lat.toFixed(3)}, ${point.lon.toFixed(3)}`} />
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage]                   = useState<Page>("landing");
  const [events, setEvents]               = useState<RiskEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<RiskEvent | null>(null);
  const [activeTab, setActiveTab]         = useState<Tab>("dashboard");
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError]     = useState<string | null>(null);

  // Map-console panel state.
  const [leftPanel, setLeftPanel]       = useState<LeftPanel>("detections");
  const [evidenceOpen, setEvidenceOpen] = useState(true);
  const [assistantOpen, setAssistantOpen] = useState(false);

  // Area-scan: click any point on the map to run YOLO on its Sentinel-1 radar,
  // independent of the GFW detections.
  const [yoloOk, setYoloOk]           = useState(false);
  const [scanMode, setScanMode]       = useState(false);
  const [scanPoint, setScanPoint]     = useState<{ lat: number; lon: number } | null>(null);
  const [scanResult, setScanResult]   = useState<YoloVerifyResult | null>(null);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanError, setScanError]     = useState<string | null>(null);

  useEffect(() => { yoloVerifyConfigured().then(setYoloOk); }, []);

  const scanActive = scanPoint !== null;

  const handleScanPick = (lat: number, lon: number) => {
    setScanPoint({ lat, lon });
    setScanResult(null);
    setScanError(null);
    setScanLoading(true);
    setAssistantOpen(false);
    verifyYolo({ lat, lon })
      .then(setScanResult)
      .catch((e) => setScanError(e instanceof Error ? e.message : "Scan failed. Try again."))
      .finally(() => setScanLoading(false));
  };

  const closeScan = () => {
    setScanMode(false);
    setScanPoint(null);
    setScanResult(null);
    setScanError(null);
    setScanLoading(false);
  };

  useEffect(() => {
    let cancelled = false;

    // Live ingestion runs in the background on the server and finishes ~30s
    // after a cold start, so we poll: detections appear (and refresh) without a
    // manual reload. The user's current selection is preserved across polls.
    const load = (initial: boolean) => {
      if (initial) { setEventsLoading(true); setEventsError(null); }
      fetchRiskEvents()
        .then((data) => {
          if (cancelled) return;
          setEvents(data);
          setEventsError(null);
          setSelectedEvent((prev) => {
            if (prev && data.some((e) => e.id === prev.id)) return prev;  // keep selection
            return data.find((e) => e.risk_level === "HIGH" || e.risk_level === "CRITICAL")
              ?? data[0] ?? null;
          });
        })
        .catch(() => {
          if (cancelled || !initial) return;  // a failed poll shouldn't wipe live data
          setEvents([]);
          setSelectedEvent(null);
          setEventsError("Couldn't load detections. Check the backend API and refresh.");
        })
        .finally(() => { if (!cancelled && initial) setEventsLoading(false); });
    };

    load(true);
    const timer = setInterval(() => load(false), 30000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  // Selecting a detection (from the map, queue, or patrol board) brings its
  // evidence to the front and steps the assistant aside so it doesn't cover it.
  const handleSelect = (e: RiskEvent) => {
    setSelectedEvent(e);
    setEvidenceOpen(true);
    setAssistantOpen(false);
    // Step the scan result aside so the detection's evidence is what's shown.
    setScanPoint(null);
    setScanResult(null);
    setScanError(null);
  };

  const handleLaunch = () => { setPage("dashboard"); setActiveTab("dashboard"); };

  const handleDemo = () => {
    setPage("dashboard");
    setActiveTab("dashboard");
    const demo =
      events.find((e) => e.id === "bar-reef-003") ||
      events.find((e) => e.risk_level === "CRITICAL") ||
      events.find((e) => e.risk_level === "HIGH");
    if (demo) handleSelect(demo);
  };

  const updateEvent = (updated: RiskEvent) => {
    setEvents((curr) => curr.map((e) => (e.id === updated.id ? updated : e)));
    setSelectedEvent((curr) => (curr?.id === updated.id ? updated : curr));
  };

  const toggleLeft = (id: Exclude<LeftPanel, null>) =>
    setLeftPanel((curr) => (curr === id ? null : id));

  const kpis = [
    { icon: Layers,        label: "Total Detections", value: events.length,                                                                                color: "text-teal-400",    bg: "bg-teal-400/8" },
    { icon: AlertTriangle, label: "High / Critical",  value: events.filter((e) => e.risk_level === "HIGH" || e.risk_level === "CRITICAL").length,           color: "text-risk-high",   bg: "bg-risk-high/8" },
    { icon: Eye,           label: "Near MPA",         value: events.filter((e) => e.inside_mpa || e.near_mpa).length,                                       color: "text-risk-medium", bg: "bg-risk-medium/8" },
    { icon: Clock,         label: "Pending Review",   value: events.filter((e) => e.review_status === "Pending").length,                                    color: "text-slate-300",   bg: "bg-slate-700/25" },
  ];

  const navChips = [
    { id: "detections" as const, icon: List,      label: "Detections" },
    { id: "briefing"   as const, icon: FileText,  label: "Briefing"   },
    { id: "patrols"    as const, icon: Crosshair, label: "Patrols"    },
  ];

  const showBackendError = eventsError && events.length === 0 && !eventsLoading;

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
        <header className="glass-dark border-b border-ocean-700/40 h-[52px] flex items-center justify-between px-4 shrink-0 z-30">
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
              { id: "dashboard" as Tab, icon: Activity,  label: "Monitoring"    },
              { id: "metrics"   as Tab, icon: BarChart3, label: "ML Validation" },
              { id: "sources"   as Tab, icon: Database,  label: "Data Sources"  },
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

        {/* Toolbar: panel navigation (left) + risk legend + KPIs + assistant (right) */}
        {activeTab === "dashboard" && (
          <div className="shrink-0 flex items-center gap-2 px-4 py-2 border-b border-ocean-700/30 bg-ocean-950/80 z-20 flex-wrap">
            {/* Panel toggles */}
            <div className="flex items-center gap-1">
              {navChips.map(({ id, icon: Icon, label }) => (
                <button
                  key={id}
                  onClick={() => toggleLeft(id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                    leftPanel === id
                      ? "bg-teal-400/12 text-teal-400 border border-teal-400/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-ocean-800/50 border border-transparent"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>

            <div className="h-5 w-px bg-ocean-700/50 mx-1 hidden sm:block" />

            {/* Risk legend */}
            <div className="hidden md:flex items-center gap-2.5">
              {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((lvl) => (
                <span key={lvl} className="flex items-center gap-1 text-[10px] text-slate-500">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: RISK_DOT[lvl] }} />
                  {lvl}
                </span>
              ))}
            </div>

            {/* KPIs + assistant pushed right */}
            <div className="ml-auto flex items-center gap-2 flex-wrap">
              {kpis.map((kpi) => {
                const Icon = kpi.icon;
                return (
                  <div
                    key={kpi.label}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg ${kpi.bg} border border-ocean-700/30`}
                  >
                    <Icon className={`w-3 h-3 ${kpi.color} shrink-0`} />
                    <span className="text-[11px] text-slate-500 hidden lg:inline">{kpi.label}:</span>
                    <span className={`text-sm font-bold ${kpi.color} tabular-nums`}>
                      <AnimatedNumber value={kpi.value} />
                    </span>
                  </div>
                );
              })}
              {eventsLoading && (
                <span className="text-[11px] text-slate-600 animate-pulse">Loading…</span>
              )}
              {yoloOk && (
                <button
                  onClick={() => { setScanMode((v) => !v); if (scanMode) closeScan(); }}
                  title="Scan any point on the map for dark vessels using our YOLO model on live Sentinel-1 radar"
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                    scanMode
                      ? "bg-cyan-400/15 text-cyan-300 border border-cyan-400/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-ocean-800/50 border border-transparent"
                  }`}
                >
                  <ScanSearch className="w-3.5 h-3.5" />
                  {scanMode ? "Click map to scan" : "Scan area"}
                </button>
              )}
              <button
                onClick={() => setAssistantOpen((v) => !v)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                  assistantOpen
                    ? "bg-teal-400/12 text-teal-400 border border-teal-400/20"
                    : "text-slate-400 hover:text-slate-200 hover:bg-ocean-800/50 border border-transparent"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                Assistant
              </button>
            </div>
          </div>
        )}

        {/* Main content */}
        <main className="flex-1 overflow-hidden relative">
          {activeTab === "dashboard" && (
            <>
              {/* Full-bleed map */}
              <div className="absolute inset-0">
                <MapView
                  events={events}
                  selected={selectedEvent}
                  onSelect={handleSelect}
                  scanMode={scanMode}
                  scanPoint={scanPoint}
                  onScanPick={handleScanPick}
                />
              </div>

              {/* Overlay panels. The layer ignores pointer events; each panel
                  re-enables them, so the map stays interactive in the gaps. */}
              <div className="absolute inset-0 pointer-events-none z-[1000]">
                <AnimatePresence>
                  {/* Left: detections / briefing / patrols */}
                  {leftPanel && !showBackendError && (
                    <Floating
                      key={leftPanel}
                      onClose={() => setLeftPanel(null)}
                      framed={leftPanel === "detections"}
                      scroll={leftPanel !== "detections"}
                      className="top-3 left-3 bottom-3 w-[330px]"
                    >
                      {leftPanel === "detections" && (
                        <RiskTable events={events} selected={selectedEvent} onSelect={handleSelect} />
                      )}
                      {leftPanel === "briefing" && <DailyBriefing events={events} />}
                      {leftPanel === "patrols"  && <PatrolBoard events={events} onSelect={handleSelect} />}
                    </Floating>
                  )}

                  {/* Right: an active area-scan wins, then the assistant, then the evidence card */}
                  {scanActive ? (
                    <Floating
                      key="scan"
                      onClose={closeScan}
                      className="top-3 right-3 bottom-3 w-[380px]"
                    >
                      <ScanPanel
                        point={scanPoint!}
                        loading={scanLoading}
                        error={scanError}
                        result={scanResult}
                      />
                    </Floating>
                  ) : assistantOpen ? (
                    <Floating
                      key="assistant"
                      onClose={() => setAssistantOpen(false)}
                      scroll={false}
                      className="top-3 right-3 bottom-3 w-[380px]"
                    >
                      <AskOceanGuard />
                    </Floating>
                  ) : (
                    selectedEvent && evidenceOpen && !showBackendError && (
                      <Floating
                        key="evidence"
                        onClose={() => setEvidenceOpen(false)}
                        className="top-3 right-3 bottom-3 w-[380px]"
                      >
                        <EvidenceCard event={selectedEvent} onUpdate={updateEvent} />
                      </Floating>
                    )
                  )}
                </AnimatePresence>

                {/* Backend offline: a single centered notice over the (empty) map */}
                {showBackendError && (
                  <div className="pointer-events-auto absolute inset-0 flex items-center justify-center p-8">
                    <div className="max-w-sm rounded-2xl border border-risk-high/20 bg-ocean-900/95 backdrop-blur-md p-8 text-center space-y-3 shadow-2xl">
                      <AlertTriangle className="w-8 h-8 text-risk-high mx-auto" />
                      <p className="font-semibold text-white">Backend Offline</p>
                      <p className="text-slate-400 text-sm">{eventsError}</p>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {activeTab === "metrics" && (
            <motion.div
              key="metrics"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 overflow-y-auto p-8"
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
              className="absolute inset-0 overflow-y-auto p-8"
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
