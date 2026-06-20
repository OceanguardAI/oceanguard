import React from "react";
import { motion, Variants } from "framer-motion";
import {
  Activity, AlertTriangle, ArrowRight, Brain, Cpu,
  Database, Eye, FileText, Gauge, Globe2, LifeBuoy,
  MapPinned, Radar, Radio, Satellite, Shield,
  ScanSearch, Waves,
} from "lucide-react";
import GradientButton from "./ui/GradientButton";
import DashboardPreview from "./landing/DashboardPreview";
import ArchitectureGraph from "./landing/ArchitectureGraph";
import LandingNavbar from "./landing/LandingNavbar";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];
const fadeUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.5, delay: i * 0.07, ease: EASE },
  }),
};

const navItems = [
  { label: "How it works",  target: "how-it-works"   },
  { label: "Workflow",      target: "workflow"        },
  { label: "Technology",    target: "technology"      },
  { label: "SDG Impact",    target: "sdg-impact"      },
  { label: "Responsible AI",target: "responsible-ai"  },
];

// Scrolling operational ticker — duplicated so the loop is seamless.
const TICKER = [
  "⬤  LIVE SYSTEM ACTIVE",
  "Sentinel-1 radar · 6–12 day global revisit",
  "Global Fishing Watch · live SAR detections feed",
  "WDPA · 10 000+ marine protected areas indexed",
  "YOLO11n detection model · mAP@50 0.838 on HRSID",
  "Gemini 2.5 Flash · evidence narrative generation",
  "Human review required before any enforcement action",
];

const problemCards = [
  { tag: "SIGNAL GAP",  title: "AIS transponders can be switched off",    copy: "Some vessels disable their public ID broadcast, becoming invisible to maritime tracking systems.", icon: Radio      },
  { tag: "CAPACITY",    title: "Manual review doesn't scale",             copy: "Thousands of daily SAR contacts exceed any team's capacity to check individually.",              icon: ScanSearch  },
  { tag: "MPA COVERAGE",title: "Protected areas need faster workflows",   copy: "Marine reserves require rapid detection triage — current processes lag by days or weeks.",       icon: MapPinned   },
];

const workflowSteps = [
  { step: "01", title: "Ingest SAR detections",   tech: "Global Fishing Watch API",        copy: "Pull worldwide vessel contacts from SAR passes. A radar return with no AIS match is the core dark-vessel signal.",                                           icon: Radio     },
  { step: "02", title: "Fetch live radar imagery", tech: "Sentinel-1 · CDSE / Copernicus", copy: "Retrieve a fresh C-band VV backscatter chip on demand. Radar penetrates cloud cover and works day and night.",                                              icon: Satellite },
  { step: "03", title: "Run our detection model",  tech: "YOLO11n · fine-tuned on HRSID",  copy: "Our own ship-detector runs on raw radar, fully independent of AIS — so it catches what the feeds miss.",                                                     icon: Cpu       },
  { step: "04", title: "Cross-reference context",  tech: "AIS broadcasts + WDPA polygons", copy: "Each contact is checked against live vessel IDs and 10 000+ marine protected area boundaries.",                                                             icon: MapPinned },
  { step: "05", title: "Score the risk",           tech: "Transparent, auditable formula", copy: "A published formula weights dark-vessel status and MPA proximity — no black box, every priority can be explained.",                                          icon: Gauge     },
  { step: "06", title: "Generate evidence card",   tech: "Gemini 2.5 Flash agents",        copy: "AI writes the narrative, daily briefing, and patrol ranking. A human officer always verifies before any action.",                                            icon: Brain     },
];

const techRows = [
  { label: "Detection model",    value: "YOLO11n",      detail: "fine-tuned on HRSID dataset · 1 class",    icon: Cpu       },
  { label: "Training data",      value: "HRSID",        detail: "~3 500 SAR images, ship class only",        icon: Database  },
  { label: "Validation quality", value: "mAP@50 0.838", detail: "held-out validation, single class",         icon: Gauge     },
  { label: "Radar sensor",       value: "Sentinel-1",   detail: "C-band VV · ESA / Copernicus free tier",    icon: Satellite },
  { label: "Live feeds",         value: "GFW · WDPA",   detail: "+ Copernicus CDSE",                         icon: Globe2    },
  { label: "AI reasoning",       value: "Gemini 2.5",   detail: "Flash agents · Vertex AI",                  icon: Brain     },
];

const impactCards = [
  { title: "Protect marine resources",   copy: "Surface suspicious activity near sensitive zones before it disappears into operational noise.", icon: Waves  },
  { title: "Support conservation teams", copy: "Give analysts a repeatable, evidence-grounded workflow for wide-area monitoring.",             icon: Globe2 },
  { title: "Focus on high-risk cases",   copy: "Turn hundreds of signals into a prioritised queue of review-ready cases, each with context.",  icon: Eye    },
];

const responsiblePrinciples = [
  { title: "Evidence-grounded outputs", copy: "Every flag includes the SAR data, AIS comparison, and MPA proximity that drove it.", icon: FileText },
  { title: "Human review first",        copy: "No action is taken automatically — officers review every evidence card.",           icon: LifeBuoy },
  { title: "No automatic accusation",   copy: "The system surfaces and explains. It never charges, fines, or accuses a vessel.",   icon: Shield   },
];

interface LandingPageProps { onLaunch: () => void; onDemo: () => void; }

export default function LandingPage({ onLaunch, onDemo }: LandingPageProps) {
  const jumpTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-h-screen overflow-x-hidden text-slate-200" style={{ background: "#040C11" }}>

      {/* ── Operational ticker ── */}
      <div className="relative overflow-hidden border-b border-amber-400/15 bg-amber-400/[0.04] py-1.5">
        <div
          className="flex items-center gap-10 whitespace-nowrap"
          style={{ animation: "ticker 55s linear infinite", willChange: "transform" }}
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
          HERO — asymmetric split
      ══════════════════════════════════════════ */}
      <section id="hero" className="relative overflow-hidden">
        <div className="absolute inset-0 ocean-grid opacity-[0.18]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_75%_55%_at_68%_50%,rgba(251,191,36,0.045),transparent)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_45%_50%_at_5%_45%,rgba(6,182,212,0.055),transparent)]" />

        <div className="relative mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-4 py-24 md:px-6 lg:grid-cols-2 lg:gap-14 lg:py-28">

          {/* Left — text */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mb-7 inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-400/8 px-3.5 py-1.5 text-[11px] uppercase tracking-[0.22em] text-amber-300"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)] animate-pulse" />
              SDG 14 · Satellite Intelligence
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.08, ease: EASE }}
              className="font-display text-[clamp(2.8rem,5.2vw,5.2rem)] font-black leading-[0.95] tracking-[-0.04em] text-white"
            >
              Making hidden<br />
              <span className="text-amber-400">ocean activity</span><br />
              visible.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.17, ease: EASE }}
              className="mt-6 max-w-lg text-lg leading-8 text-slate-400"
            >
              Satellite radar catches vessels that turn their ID transponders off.
              OceanGuard turns those detections into reviewed evidence cards —
              in minutes, not days.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.26, ease: EASE }}
              className="mt-8 flex flex-wrap items-center gap-3"
            >
              <GradientButton variant="primary" size="lg" onClick={onLaunch}>
                Open Dashboard <ArrowRight className="h-4 w-4" />
              </GradientButton>
              <GradientButton variant="secondary" size="lg" onClick={() => jumpTo("how-it-works")}>
                See How It Works
              </GradientButton>
            </motion.div>

            {/* Inline stat strip */}
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.42 }}
              className="mt-10 flex flex-wrap gap-x-8 gap-y-4 border-t border-white/8 pt-8"
            >
              {[
                { value: "$23B",  label: "lost to IUU fishing / yr" },
                { value: "1 in 5",label: "fish caught illegally"    },
                { value: "0.838", label: "model mAP@50"             },
              ].map(({ value, label }) => (
                <div key={label} className="flex flex-col gap-0.5">
                  <span className="font-mono text-2xl font-bold text-white">{value}</span>
                  <span className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{label}</span>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right — live dashboard preview */}
          <motion.div
            initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.28, ease: EASE }}
            className="relative"
          >
            <div className="absolute -top-3 -right-3 z-10 flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-[#040C11]/90 px-2.5 py-1 text-[10px] font-mono font-semibold text-amber-300 shadow-lg backdrop-blur-md">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              LIVE DETECTIONS
            </div>
            <div className="overflow-hidden rounded-xl border border-white/10 shadow-[0_24px_80px_rgba(0,0,0,0.65)]">
              <DashboardPreview />
            </div>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-amber-400/25 to-transparent" />
          </motion.div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          SCALE BAND
      ══════════════════════════════════════════ */}
      <div className="border-y border-white/6 bg-[#030A0E] py-12">
        <div className="mx-auto max-w-7xl px-4 md:px-6">
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-white/8 bg-white/5 md:grid-cols-4">
            {[
              { value: "$23B",    label: "Lost to IUU fishing",   sub: "per year · FAO estimate",   accent: "text-amber-400" },
              { value: "1 in 5",  label: "Fish caught illegally", sub: "of the global marine catch", accent: "text-amber-300" },
              { value: "Global",  label: "Free SAR coverage",     sub: "Sentinel-1 · all weather",   accent: "text-cyan-400"  },
              { value: "Minutes", label: "Signal to evidence",    sub: "vs days of manual review",   accent: "text-teal-400"  },
            ].map((s) => (
              <div key={s.label} className="bg-[#040C11] p-6 text-center md:p-8">
                <div className={`font-mono text-3xl font-bold md:text-4xl ${s.accent}`}>{s.value}</div>
                <div className="mt-2 text-sm font-semibold text-white">{s.label}</div>
                <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-500">{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════
          PROBLEM
      ══════════════════════════════════════════ */}
      <section id="problem" className="px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp}
            className="mb-12 grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end"
          >
            <div>
              <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5" /> The challenge
              </div>
              <h2 className="font-display text-4xl font-black text-white md:text-5xl">
                The ocean is too large<br className="hidden md:block" /> to monitor manually.
              </h2>
            </div>
            <p className="max-w-sm text-sm leading-7 text-slate-500 lg:text-right">
              Some vessels don't appear in public tracking systems. Teams need faster ways to find which satellite contacts deserve review.
            </p>
          </motion.div>

          <div className="grid gap-4 md:grid-cols-3">
            {problemCards.map((card, i) => {
              const Icon = card.icon;
              return (
                <motion.div key={card.title}
                  initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={i + 1} variants={fadeUp}
                  className="group relative overflow-hidden rounded-xl border border-white/8 bg-white/[0.025] p-6 transition-all duration-300 hover:border-amber-400/20 hover:bg-amber-400/[0.025]"
                >
                  <div className="mb-4 inline-flex items-center rounded-md border border-amber-400/15 bg-amber-400/8 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-amber-400/70">
                    {card.tag}
                  </div>
                  <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                    <Icon className="h-5 w-5 text-cyan-300" />
                  </div>
                  <h3 className="font-display text-lg font-semibold text-white">{card.title}</h3>
                  <p className="mt-2.5 text-sm leading-7 text-slate-400">{card.copy}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          HOW IT WORKS — keeps ArchitectureGraph
      ══════════════════════════════════════════ */}
      <section id="how-it-works" className="border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mb-10">
            <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-400">
              <Radar className="h-3.5 w-3.5" /> Pipeline
            </div>
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              From signal to evidence card.
            </h2>
          </motion.div>
          <ArchitectureGraph />
        </div>
      </section>

      {/* ══════════════════════════════════════════
          WORKFLOW — numbered timeline, not a grid
      ══════════════════════════════════════════ */}
      <section id="workflow" className="relative overflow-hidden border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="absolute inset-0 ocean-grid opacity-[0.12]" />
        <div className="relative mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mb-14">
            <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-400">
              <Activity className="h-3.5 w-3.5" /> Technical workflow
            </div>
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              Six stages. Fully auditable.
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-slate-400">
              Each stage runs independently of vessel-reported data — so the system surfaces activity that transponder broadcasts alone would miss.
            </p>
          </motion.div>

          {/* Timeline — single vertical list */}
          <div>
            {workflowSteps.map((s, i) => {
              const Icon = s.icon;
              const isLast = i === workflowSteps.length - 1;
              return (
                <motion.div key={s.step}
                  initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i} variants={fadeUp}
                  className="group relative grid grid-cols-[48px_1fr] items-start gap-6 border-t border-white/6 py-6 transition-colors duration-200 hover:bg-white/[0.012] md:grid-cols-[64px_1fr_260px]"
                >
                  {/* Step number + connector */}
                  <div className="flex flex-col items-center">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 font-mono text-xs font-bold text-slate-500 transition-colors group-hover:border-cyan-400/20 group-hover:text-cyan-300">
                      {s.step}
                    </div>
                    {!isLast && <div className="mt-2 w-px flex-1 min-h-[24px] bg-gradient-to-b from-white/8 to-transparent" />}
                  </div>

                  {/* Content */}
                  <div className="pb-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2.5">
                      <Icon className="h-4 w-4 shrink-0 text-cyan-400" />
                      <h3 className="font-display text-lg font-semibold text-white">{s.title}</h3>
                      <span className="rounded-full border border-teal-400/15 bg-teal-400/5 px-2.5 py-0.5 font-mono text-[10px] text-teal-200/75">
                        {s.tech}
                      </span>
                    </div>
                    <p className="max-w-xl text-sm leading-7 text-slate-400">{s.copy}</p>
                  </div>

                  {/* Icon echo (desktop) */}
                  <div className="hidden items-center justify-end md:flex">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/6 bg-white/[0.02] opacity-30 transition-opacity group-hover:opacity-70">
                      <Icon className="h-4 w-4 text-slate-300" />
                    </div>
                  </div>
                </motion.div>
              );
            })}
            {/* close the last border */}
            <div className="border-t border-white/6" />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          TECH SPECS — spec-table, not cards
      ══════════════════════════════════════════ */}
      <section id="technology" className="border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mb-10">
            <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-400">
              <Cpu className="h-3.5 w-3.5" /> Under the hood
            </div>
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              The full technical stack.
            </h2>
          </motion.div>

          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={1} variants={fadeUp}
            className="overflow-hidden rounded-xl border border-white/8"
          >
            {techRows.map((row, i) => {
              const Icon = row.icon;
              return (
                <div key={row.label}
                  className={`grid grid-cols-[1fr_auto] items-center gap-4 px-5 py-4 transition-colors hover:bg-white/[0.025] md:grid-cols-[200px_1fr_auto] ${i !== techRows.length - 1 ? "border-b border-white/6" : ""}`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-3.5 w-3.5 shrink-0 text-slate-600" />
                    <span className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{row.label}</span>
                  </div>
                  <div className="font-mono text-base font-bold text-white">{row.value}</div>
                  <div className="hidden text-right font-mono text-xs text-slate-600 md:block">{row.detail}</div>
                </div>
              );
            })}
          </motion.div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          SDG IMPACT
      ══════════════════════════════════════════ */}
      <section id="sdg-impact" className="relative overflow-hidden border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="absolute inset-0 ocean-contours opacity-[0.18]" />
        <div className="relative mx-auto max-w-7xl">
          <div className="grid items-start gap-10 lg:grid-cols-2 lg:gap-16">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp}>
              <div className="mb-4 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-teal-400">
                <Waves className="h-3.5 w-3.5" /> Built for SDG 14
              </div>
              <h2 className="font-display text-4xl font-black text-white md:text-5xl">
                Life Below Water.
              </h2>
              <p className="mt-6 text-base leading-8 text-slate-400">
                OceanGuard supports responsible ocean monitoring — helping teams review vessel activity near protected marine areas and prioritise conservation attention where it matters most.
              </p>
              <div className="mt-8 inline-flex items-center gap-3 rounded-xl border border-teal-400/15 bg-teal-400/[0.05] px-4 py-3">
                <Globe2 className="h-5 w-5 shrink-0 text-teal-400" />
                <span className="text-sm text-slate-300">
                  <span className="font-semibold text-teal-300">SDG 14.6</span> — reduce illegal, unreported and unregulated fishing
                </span>
              </div>
            </motion.div>

            <div className="space-y-3">
              {impactCards.map((card, i) => {
                const Icon = card.icon;
                return (
                  <motion.div key={card.title}
                    initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={i + 1} variants={fadeUp}
                    className="flex items-start gap-4 rounded-xl border border-white/8 bg-white/[0.025] p-5 transition-colors hover:border-teal-400/15"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-teal-400/15 bg-teal-400/8">
                      <Icon className="h-4 w-4 text-teal-300" />
                    </div>
                    <div>
                      <div className="font-display font-semibold text-white">{card.title}</div>
                      <p className="mt-1 text-sm leading-6 text-slate-400">{card.copy}</p>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          RESPONSIBLE AI
      ══════════════════════════════════════════ */}
      <section id="responsible-ai" className="border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <div className="overflow-hidden rounded-2xl border border-amber-400/15 bg-amber-400/[0.03]">
            {/* Amber accent bar */}
            <div className="h-0.5 w-full bg-gradient-to-r from-amber-400/40 via-amber-400/70 to-transparent" />
            <div className="grid gap-10 p-8 lg:grid-cols-2 lg:gap-16 md:p-10">
              <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp}>
                <div className="mb-4 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-amber-400">
                  <Shield className="h-3.5 w-3.5" /> Responsible AI
                </div>
                <h2 className="font-display text-4xl font-black text-white md:text-5xl">
                  Decision support,<br className="hidden md:block" /> not automatic action.
                </h2>
                <p className="mt-5 text-base leading-8 text-slate-400">
                  OceanGuard flags possible risk signals and explains the evidence. Every output is designed for human verification before any action is taken.
                </p>
              </motion.div>

              <div className="space-y-3">
                {responsiblePrinciples.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <motion.div key={item.title}
                      initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={i + 1} variants={fadeUp}
                      className="flex items-start gap-4 rounded-xl border border-amber-400/10 bg-amber-400/[0.03] p-4"
                    >
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-amber-400/15 bg-amber-400/8">
                        <Icon className="h-4 w-4 text-amber-300" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-white">{item.title}</div>
                        <p className="mt-0.5 text-xs leading-5 text-slate-400">{item.copy}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          CTA
      ══════════════════════════════════════════ */}
      <section className="px-4 pb-24 pt-4 md:px-6">
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}
          className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-[#040C11]"
        >
          <div className="h-0.5 w-full bg-gradient-to-r from-amber-400/50 via-amber-400 to-teal-400/50" />
          <div className="px-8 py-12 text-center md:px-12 md:py-14">
            <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-400/8 px-3.5 py-1.5 text-[11px] uppercase tracking-[0.22em] text-amber-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
              System active
            </div>
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              Start reviewing ocean risk<br className="hidden md:block" /> with satellite AI.
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-base leading-8 text-slate-400">
              Open the live dashboard and explore how satellite detections become reviewed evidence cards.
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
          <div className="text-center font-mono text-xs text-slate-600 md:text-right">
            OceanGuard provides decision-support analysis only. AI outputs must be verified by a human conservation officer before any enforcement action.
          </div>
        </div>
      </footer>
    </div>
  );
}
