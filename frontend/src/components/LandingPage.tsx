import React from "react";
import { motion, Variants } from "framer-motion";
import {
  AlertTriangle, ArrowRight, CheckCircle2,
  Eye, FileText, MapPinned, Radio, ScanSearch,
} from "lucide-react";
import GradientButton from "./ui/GradientButton";
import HeroAnimation from "./landing/HeroAnimation";
import LandingNavbar from "./landing/LandingNavbar";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];
const fadeUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.5, delay: i * 0.08, ease: EASE },
  }),
};

const navItems = [
  { label: "The Problem",   target: "problem"  },
  { label: "Our Solution",  target: "solution" },
];

const TICKER = [
  "⬤  LIVE SYSTEM ACTIVE",
  "Sentinel-1 radar · global ocean coverage",
  "Global Fishing Watch · live SAR detections",
  "WDPA · 10 000+ marine protected areas indexed",
  "YOLO11n detection model · mAP@50 0.838",
  "AI evidence cards · human review required",
];

const PROBLEMS = [
  { icon: Radio,     title: "Ships go dark",             copy: "Vessels switch off their AIS transponders to hide. No public tracking system sees them — but satellite radar does." },
  { icon: ScanSearch,title: "Too many contacts to check", copy: "Thousands of satellite detections arrive daily. No team has the capacity to inspect them one by one." },
  { icon: MapPinned, title: "Protected areas go unwatched", copy: "Marine reserves need rapid triage. By the time an alert is reviewed, the vessel has long gone." },
];

const SOLUTIONS = [
  { icon: Eye,         title: "Radar sees what AIS hides",     copy: "Sentinel-1 SAR satellites photograph the entire ocean day and night, through clouds — vessel on or off, they show up." },
  { icon: ScanSearch,  title: "AI scores every contact",        copy: "Our model runs on the raw radar. Each contact is ranked by risk — dark vessel + inside a protected area = investigate first." },
  { icon: FileText,    title: "Officers get a clear case file", copy: "One evidence card per detection: radar image, plain-English explanation, and review buttons. Human judgement stays in the loop." },
];

interface Props { onLaunch: () => void; onDemo: () => void; }

export default function LandingPage({ onLaunch, onDemo }: Props) {
  const jumpTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="min-h-screen overflow-x-hidden text-slate-200" style={{ background: "#040C11" }}>

      {/* ── Live operations ticker ── */}
      <div className="relative overflow-hidden border-b border-amber-400/15 bg-amber-400/[0.04] py-1.5">
        <div
          className="flex items-center gap-10 whitespace-nowrap"
          style={{ animation: "ticker 50s linear infinite", willChange: "transform" }}
        >
          {[...TICKER, ...TICKER].map((item, i) => (
            <span key={i} className="flex shrink-0 items-center gap-3">
              {i % TICKER.length === 0
                ? <span className="font-mono text-[11px] font-bold text-amber-400">{item}</span>
                : <><span className="text-amber-400/20">│</span><span className="font-mono text-[11px] text-amber-200/50">{item}</span></>
              }
            </span>
          ))}
        </div>
      </div>

      <LandingNavbar items={navItems} onOpenDashboard={onLaunch} onJump={jumpTo} />

      {/* ══════════════════════════════════════════
          HERO
      ══════════════════════════════════════════ */}
      <section id="hero" className="relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse 80% 60% at 70% 50%, rgba(251,191,36,0.04), transparent)" }} />
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse 45% 55% at 5% 45%, rgba(6,182,212,0.05), transparent)" }} />

        <div className="relative mx-auto grid max-w-7xl grid-cols-1 items-center gap-10 px-4 py-24 md:px-6 lg:grid-cols-2 lg:gap-12 lg:py-28">

          {/* Left: copy */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-7 inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-400/8 px-3.5 py-1.5 text-[11px] uppercase tracking-[0.22em] text-amber-300"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)] animate-pulse" />
              SDG 14 · Satellite Intelligence
            </motion.div>

            {/* Name reveal — clips left to right */}
            <div className="overflow-hidden mb-2">
              <motion.div
                initial={{ y: "110%" }} animate={{ y: 0 }}
                transition={{ duration: 0.55, delay: 0.05, ease: EASE }}
                className="font-mono text-xs uppercase tracking-[0.25em] text-slate-500"
              >
                OceanGuard AI
              </motion.div>
            </div>

            <motion.h1
              initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1, ease: EASE }}
              className="font-display text-[clamp(2.8rem,5.2vw,5.4rem)] font-black leading-[0.95] tracking-[-0.04em] text-white"
            >
              Making hidden<br />
              <span className="text-amber-400">ocean activity</span><br />
              visible.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.2, ease: EASE }}
              className="mt-6 max-w-lg text-lg leading-8 text-slate-400"
            >
              Satellite radar catches vessels that switch their tracking off.
              OceanGuard turns those detections into reviewed evidence cards —
              in minutes, not days.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3, ease: EASE }}
              className="mt-8 flex flex-wrap items-center gap-3"
            >
              <GradientButton variant="primary" size="lg" onClick={onLaunch}>
                Open Dashboard <ArrowRight className="h-4 w-4" />
              </GradientButton>
              <GradientButton variant="secondary" size="lg" onClick={() => jumpTo("problem")}>
                How It Works
              </GradientButton>
            </motion.div>

            {/* Quick stats */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.45 }}
              className="mt-10 flex flex-wrap gap-x-8 gap-y-4 border-t border-white/8 pt-8"
            >
              {[
                { value: "$23B",  label: "lost to illegal fishing / yr" },
                { value: "1 in 5",label: "fish caught outside the rules" },
                { value: "Minutes",label: "from satellite to evidence"   },
              ].map(({ value, label }) => (
                <div key={label}>
                  <div className="font-mono text-2xl font-bold text-white">{value}</div>
                  <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{label}</div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right: animated satellite view */}
          <motion.div
            initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.25, ease: EASE }}
            className="relative"
          >
            <div className="absolute -top-3 -right-3 z-10 flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-[#040C11]/90 px-2.5 py-1 text-[10px] font-mono font-semibold text-amber-300 shadow-lg backdrop-blur-md">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              LIVE SATELLITE SCAN
            </div>
            <HeroAnimation />
          </motion.div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          PROBLEM + SOLUTION (one section, two columns)
      ══════════════════════════════════════════ */}
      <section id="problem" className="border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">

          {/* Section label */}
          <motion.div
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}
            className="mb-14 text-center"
          >
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              A real problem. A clear answer.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-8 text-slate-500">
              Illegal fishing costs the world $23 billion a year. The ocean is too large to watch manually — but not for a satellite.
            </p>
          </motion.div>

          <div className="grid gap-8 lg:grid-cols-2 lg:gap-12">

            {/* PROBLEM column */}
            <div>
              <motion.div
                initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}
                className="mb-6 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-amber-400"
              >
                <AlertTriangle className="h-3.5 w-3.5" />
                The challenge
              </motion.div>
              <div className="space-y-3">
                {PROBLEMS.map((p, i) => {
                  const Icon = p.icon;
                  return (
                    <motion.div key={p.title}
                      initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i + 1} variants={fadeUp}
                      className="flex items-start gap-4 rounded-xl border border-amber-400/10 bg-amber-400/[0.03] p-4 transition-colors hover:border-amber-400/20"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-amber-400/15 bg-amber-400/8">
                        <Icon className="h-4 w-4 text-amber-300" />
                      </div>
                      <div>
                        <div className="font-display font-semibold text-white">{p.title}</div>
                        <p className="mt-0.5 text-sm leading-6 text-slate-400">{p.copy}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>

            {/* SOLUTION column */}
            <div id="solution">
              <motion.div
                initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}
                className="mb-6 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-400"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Our answer
              </motion.div>
              <div className="space-y-3">
                {SOLUTIONS.map((s, i) => {
                  const Icon = s.icon;
                  return (
                    <motion.div key={s.title}
                      initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i + 1} variants={fadeUp}
                      className="flex items-start gap-4 rounded-xl border border-cyan-400/10 bg-cyan-400/[0.03] p-4 transition-colors hover:border-cyan-400/20"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-cyan-400/15 bg-cyan-400/8">
                        <Icon className="h-4 w-4 text-cyan-300" />
                      </div>
                      <div>
                        <div className="font-display font-semibold text-white">{s.title}</div>
                        <p className="mt-0.5 text-sm leading-6 text-slate-400">{s.copy}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Responsible AI notice — small, honest */}
          <motion.p
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={0} variants={fadeUp}
            className="mx-auto mt-12 max-w-2xl text-center text-sm leading-7 text-slate-600"
          >
            OceanGuard does not accuse vessels. It surfaces evidence and explains it. A human officer reviews every case before any action is taken.
          </motion.p>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          CTA
      ══════════════════════════════════════════ */}
      <section className="px-4 pb-24 pt-4 md:px-6">
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}
          className="mx-auto max-w-4xl overflow-hidden rounded-2xl border border-white/10 bg-[#040C11]"
        >
          <div className="h-0.5 bg-gradient-to-r from-amber-400/50 via-amber-400 to-teal-400/50" />
          <div className="px-8 py-12 text-center md:px-10 md:py-14">
            <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-400/8 px-3.5 py-1.5 text-[11px] uppercase tracking-[0.22em] text-amber-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              System active
            </div>
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              See hidden vessels.<br className="hidden md:block" /> Review the evidence.
            </h2>
            <p className="mx-auto mt-5 max-w-lg text-base leading-8 text-slate-400">
              Open the live dashboard — real satellite detections, AI evidence cards, human review built in.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <GradientButton variant="primary" size="lg" onClick={onLaunch}>
                Open Dashboard <ArrowRight className="h-4 w-4" />
              </GradientButton>
              <GradientButton variant="secondary" size="lg" onClick={onDemo}>
                View Live Demo
              </GradientButton>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-white/6 px-4 py-8 md:px-6">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-3">
            <img src="/branding/oceanguard-mark.png" alt="OceanGuard AI" className="h-8 w-8 rounded-lg object-cover" />
            <div>
              <div className="font-display font-bold text-white">OceanGuard AI</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Conservation intelligence</div>
            </div>
          </div>
          <p className="text-center font-mono text-xs text-slate-600 md:text-right">
            Decision-support only. All outputs require human verification before any enforcement action.
          </p>
        </div>
      </footer>
    </div>
  );
}
