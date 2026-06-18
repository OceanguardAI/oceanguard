import React from "react";
import { motion, Variants } from "framer-motion";
import {
  ShieldAlert, Satellite, Radio, Map, BarChart3,
  FileText, Users, ChevronRight, Zap, Eye, AlertTriangle,
} from "lucide-react";
import GradientButton from "./ui/GradientButton";
import RiskBadge from "./ui/RiskBadge";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.09, ease: EASE },
  }),
};

const BENTO = [
  { icon: Satellite, title: "SAR Detection", desc: "YOLO11n trained on HRSID detects vessels in Sentinel-1 imagery through clouds, at night, over 1000s of km².", span: false },
  { icon: Radio,     title: "AIS Cross-Check", desc: "Every detection is matched against Global Fishing Watch AIS broadcasts. No match = Dark vessel = elevated risk.", span: false },
  { icon: Map,       title: "MPA Geospatial", desc: "Vessels inside or within 5 km of a Marine Protected Area are automatically escalated to high/critical risk.", span: false },
  { icon: BarChart3, title: "Risk Scoring", desc: "Transparent, deterministic formula: SAR confidence × AIS status × MPA proximity × port distance. No black box.", span: false },
  { icon: FileText,  title: "AI Evidence Card", desc: "Gemini generates a human-readable brief per detection — explaining why it was flagged and what uncertainty remains. Officers see the reasoning, not just a score.", span: true },
  { icon: Users,     title: "Human Review", desc: "All AI outputs are advisory. Officers confirm or dismiss each flag. No automated enforcement.", span: false },
];

const STEPS = [
  { num: "01", title: "SAR Satellite Pass",  desc: "Sentinel-1 images coastal MPA zones on a regular orbital cadence." },
  { num: "02", title: "Vessel Detection",    desc: "YOLO11n locates vessel-shaped bright objects in the SAR image with confidence scores." },
  { num: "03", title: "AIS Correlation",    desc: "Each detection window is checked against GFW AIS data. Missing signal → dark flag." },
  { num: "04", title: "Risk Scoring",       desc: "Deterministic formula produces a 0–100 score from AIS status, MPA distance, SAR confidence." },
  { num: "05", title: "AI Evidence Brief",  desc: "Gemini writes a natural-language explanation of why the vessel was flagged, with uncertainty." },
  { num: "06", title: "Officer Review",     desc: "Patrol board ranks detections. Officers review the evidence and decide on enforcement." },
];

interface LandingPageProps {
  onLaunch: () => void;
  onDemo: () => void;
}

export default function LandingPage({ onLaunch, onDemo }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-ocean-950 overflow-x-hidden text-slate-200">

      {/* ── Navigation ─────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-3.5 glass-dark">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center shadow-lg shadow-teal-500/30">
            <ShieldAlert className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-bold text-white tracking-tight">
            OceanGuard <span className="text-gradient">AI</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <GradientButton variant="ghost" size="sm" onClick={onLaunch}>
            Dashboard
          </GradientButton>
          <GradientButton variant="primary" size="sm" onClick={onLaunch}>
            Launch <ChevronRight className="w-3.5 h-3.5" />
          </GradientButton>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center text-center px-6 pt-20 pb-24 overflow-hidden">
        {/* animated aurora */}
        <div className="absolute inset-0 aurora-bg opacity-70 pointer-events-none" />
        {/* floating blobs */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 left-1/5 w-[500px] h-[500px] bg-teal-500/8 rounded-full blur-[100px] animate-float" />
          <div className="absolute top-1/3 right-1/5 w-[380px] h-[380px] bg-blue-500/6 rounded-full blur-[80px] animate-float" style={{ animationDelay: "2.5s" }} />
          <div className="absolute bottom-1/4 left-1/3 w-[300px] h-[300px] bg-teal-300/5 rounded-full blur-[70px] animate-float" style={{ animationDelay: "4.5s" }} />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-teal-400/25 bg-teal-400/5 text-teal-300 text-xs font-semibold uppercase tracking-widest mb-10"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
            Maritime Intelligence · Live Demo Ready
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="text-[clamp(3rem,8vw,5.5rem)] font-black text-white leading-[1.03] tracking-tight mb-5"
          >
            OceanGuard&nbsp;<span className="text-gradient">AI</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
            className="text-xl md:text-2xl text-slate-300 font-medium mb-4 leading-snug"
          >
            Detect dark fishing risk near Marine Protected Areas.
          </motion.p>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.26, ease: [0.22, 1, 0.36, 1] }}
            className="text-slate-400 max-w-2xl mx-auto mb-12 leading-relaxed"
          >
            SAR vessel detection · AIS cross-checking · MPA geospatial analysis ·
            deterministic risk scoring · AI-generated evidence cards for human reviewers.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.34 }}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            <GradientButton variant="primary" size="lg" onClick={onLaunch}>
              <Zap className="w-5 h-5" /> Launch Dashboard
            </GradientButton>
            <GradientButton variant="secondary" size="lg" onClick={onDemo}>
              <Eye className="w-5 h-5" /> View Critical Demo
            </GradientButton>
          </motion.div>

          {/* Stat chips */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, delay: 0.55 }}
            className="mt-20 flex flex-wrap items-center justify-center gap-6"
          >
            {[
              { val: "YOLO11n",     label: "Detection Model"   },
              { val: "Sentinel-1",  label: "SAR Satellite"     },
              { val: "Bar Reef",    label: "Protected Zone"    },
              { val: "Gemini AI",   label: "Evidence Agent"    },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-base font-bold text-white">{s.val}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Problem ────────────────────────────────────────────── */}
      <section className="py-28 px-6 max-w-6xl mx-auto">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }}
          custom={0} variants={fadeUp} className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-risk-high mb-4">
            <AlertTriangle className="w-3.5 h-3.5" /> The Problem
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">Illegal Fishing Is Invisible</h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-lg leading-relaxed">
            Dark vessels disable their AIS transponders to avoid detection inside MPAs.
            Traditional surveillance can't see them — but SAR satellites can.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {[
            { icon: "🌊", stat: "~26M",  label: "tonnes of fish illegally caught each year" },
            { icon: "📡", stat: "~30%",  label: "of fishing vessels go dark near MPAs"      },
            { icon: "🛰️", stat: "24/7",  label: "SAR imaging: clouds, night, no barrier"   },
          ].map((item, i) => (
            <motion.div key={item.label} initial="hidden" whileInView="visible"
              viewport={{ once: true }} custom={i + 1} variants={fadeUp}
              className="glass rounded-2xl p-8 text-center"
            >
              <div className="text-4xl mb-4">{item.icon}</div>
              <div className="text-3xl font-extrabold text-white mb-2">{item.stat}</div>
              <div className="text-sm text-slate-400">{item.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Feature Bento ──────────────────────────────────────── */}
      <section className="py-28 px-6 max-w-6xl mx-auto">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }}
          custom={0} variants={fadeUp} className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-teal-400 mb-4">
            <Zap className="w-3.5 h-3.5" /> Core Capabilities
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">Intelligence. Fused. Explainable.</h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Six systems working together to surface real fishing risk in real time.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {BENTO.map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.div key={item.title} initial="hidden" whileInView="visible"
                viewport={{ once: true }} custom={i + 1} variants={fadeUp}
                className={`glass rounded-2xl p-7 hover:border-teal-400/20 transition-all duration-300 group ${item.span ? "md:col-span-2" : ""}`}
              >
                <div className="w-10 h-10 rounded-xl bg-teal-400/8 border border-teal-400/15 flex items-center justify-center mb-5 group-hover:bg-teal-400/15 transition-colors">
                  <Icon className="w-5 h-5 text-teal-400" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{item.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ── How It Works ───────────────────────────────────────── */}
      <section className="py-28 px-6 max-w-6xl mx-auto">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }}
          custom={0} variants={fadeUp} className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-teal-400 mb-4">
            How It Works
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">From Satellite to Patrol</h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Six automated steps turn raw SAR imagery into actionable patrol recommendations.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {STEPS.map((step, i) => (
            <motion.div key={step.num} initial="hidden" whileInView="visible"
              viewport={{ once: true }} custom={i + 1} variants={fadeUp}
              className="glass rounded-2xl p-7 relative overflow-hidden"
            >
              <div className="absolute -top-2 -right-1 text-7xl font-black text-ocean-700/60 select-none leading-none pointer-events-none">
                {step.num}
              </div>
              <h3 className="text-white font-semibold mb-2 relative z-10">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed relative z-10">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Live Demo CTA ──────────────────────────────────────── */}
      <section className="py-24 px-6">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }}
          custom={0} variants={fadeUp} className="max-w-3xl mx-auto text-center"
        >
          <div className="relative rounded-3xl overflow-hidden border border-teal-400/15">
            <div className="absolute inset-0 aurora-bg opacity-40 pointer-events-none" />
            <div className="relative z-10 p-14">
              <div className="flex items-center justify-center gap-3 mb-6">
                <RiskBadge level="CRITICAL" />
                <span className="text-sm text-slate-400">bar-reef-003 · Live Detection</span>
              </div>
              <h2 className="text-4xl font-extrabold text-white mb-4">See It In Action</h2>
              <p className="text-slate-400 mb-10 max-w-lg mx-auto leading-relaxed">
                The dashboard is pre-loaded with a critical demo: a dark vessel detected inside Bar Reef MPA.
                Follow the complete detection-to-review workflow.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-4">
                <GradientButton variant="primary" size="lg" onClick={onDemo}>
                  <Eye className="w-5 h-5" /> View Critical Demo
                </GradientButton>
                <GradientButton variant="secondary" size="lg" onClick={onLaunch}>
                  <Zap className="w-5 h-5" /> Full Dashboard
                </GradientButton>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── Responsible AI ─────────────────────────────────────── */}
      <section className="py-16 px-6 border-t border-ocean-700/30">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">
            <AlertTriangle className="w-3.5 h-3.5 text-risk-medium" /> Responsible AI Notice
          </div>
          <p className="text-slate-500 text-sm leading-relaxed max-w-2xl mx-auto">
            OceanGuard AI outputs are decision-support only. All risk flags include explicit uncertainty disclosures.
            Human conservation officers must review and approve any enforcement action.
            No automated enforcement. No punitive action without human review.
          </p>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="py-8 px-6 border-t border-ocean-700/20">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center">
              <ShieldAlert className="w-2.5 h-2.5 text-white" />
            </div>
            <span className="text-sm font-bold text-white">OceanGuard AI</span>
          </div>
          <p className="text-xs text-slate-600">
            Maritime intelligence for human reviewers · Not for automated enforcement
          </p>
        </div>
      </footer>
    </div>
  );
}
