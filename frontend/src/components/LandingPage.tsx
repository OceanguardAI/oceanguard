import React from "react";
import { motion, Variants } from "framer-motion";
import {
  ActivitySquare,
  AlertTriangle,
  ArrowRight,
  Brain,
  Cpu,
  Database,
  Eye,
  FileText,
  Gauge,
  Globe2,
  LifeBuoy,
  MapPinned,
  Radar,
  Radio,
  Satellite,
  ScanSearch,
  Shield,
  Sparkles,
  Waves,
} from "lucide-react";
import GradientButton from "./ui/GradientButton";
import DashboardPreview from "./landing/DashboardPreview";
import ArchitectureGraph from "./landing/ArchitectureGraph";
import LandingNavbar from "./landing/LandingNavbar";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, delay: i * 0.08, ease: EASE },
  }),
};

const navItems = [
  { label: "How it works", target: "how-it-works" },
  { label: "Workflow", target: "workflow" },
  { label: "Technology", target: "technology" },
  { label: "SDG Impact", target: "sdg-impact" },
  { label: "Responsible AI", target: "responsible-ai" },
];

const problemCards = [
  {
    title: "AIS gaps",
    copy: "Some vessels may be missing or difficult to verify from tracking data alone.",
    icon: Radio,
  },
  {
    title: "Manual review is slow",
    copy: "Large ocean areas create too many satellite detections for manual inspection.",
    icon: ScanSearch,
  },
  {
    title: "Protected areas need focus",
    copy: "Marine protected areas need faster risk prioritization and review workflows.",
    icon: MapPinned,
  },
];

const solutionCards = [
  { title: "Detect vessel-like activity from SAR imagery", icon: Eye },
  { title: "Compare detections with AIS evidence", icon: ActivitySquare },
  { title: "Check protected-area proximity", icon: Globe2 },
  { title: "Generate clear evidence cards for human review", icon: FileText },
];

const impactCards = [
  {
    title: "Protect marine resources",
    copy: "Highlight activity near sensitive waters before it becomes invisible operational noise.",
    icon: Waves,
  },
  {
    title: "Support sustainable monitoring",
    copy: "Give conservation teams a repeatable, evidence-grounded workflow for wide-area review.",
    icon: Globe2,
  },
  {
    title: "Help analysts focus on high-risk cases",
    copy: "Turn hundreds of signals into a smaller queue of review-ready cases with context.",
    icon: Sparkles,
  },
];

const responsiblePrinciples = [
  { title: "Evidence-grounded outputs", icon: FileText },
  { title: "Human review first", icon: LifeBuoy },
  { title: "No automatic accusation", icon: Shield },
];

// The real end-to-end pipeline, named at each stage so technical reviewers can
// see exactly how a satellite signal becomes a review-ready case.
const workflowSteps = [
  {
    step: "01",
    title: "Ingest global detections",
    tech: "Global Fishing Watch API",
    copy: "Pull SAR vessel detections worldwide. A radar hit with no matching AIS identity is the core dark-vessel signal.",
    icon: Radio,
  },
  {
    step: "02",
    title: "Pull live radar imagery",
    tech: "Sentinel-1 · Copernicus (CDSE)",
    copy: "Fetch a fresh Sentinel-1 C-band VV backscatter chip for the area on demand. Radar sees through cloud, day or night.",
    icon: Satellite,
  },
  {
    step: "03",
    title: "Detect with our own model",
    tech: "YOLO11n · fine-tuned on SAR",
    copy: "Run our ship-detection model directly on the raw radar — fully independent of AIS, so it catches vessels the feeds miss.",
    icon: Cpu,
  },
  {
    step: "04",
    title: "Cross-reference context",
    tech: "AIS · WDPA protected areas",
    copy: "Check each contact against live AIS broadcasts and protected-area boundaries to separate routine traffic from anomalies.",
    icon: MapPinned,
  },
  {
    step: "05",
    title: "Score the risk",
    tech: "Deterministic, auditable formula",
    copy: "A transparent score weights AIS gaps and MPA proximity — no black box, so every priority can be explained.",
    icon: Gauge,
  },
  {
    step: "06",
    title: "Explain for human review",
    tech: "Gemini 2.5 Flash agents",
    copy: "AI writes the evidence card, daily briefing, and patrol ranking. A human officer verifies before any action.",
    icon: Brain,
  },
];

// Honest, concrete numbers about what's under the hood.
const techStack = [
  { label: "Detection model", value: "YOLO11n", sub: "fine-tuned", icon: Cpu },
  { label: "Training data", value: "HRSID", sub: "~3.5k SAR images", icon: Database },
  { label: "Detection quality", value: "mAP@50 0.838", sub: "on validation", icon: Gauge },
  { label: "Radar sensor", value: "Sentinel-1", sub: "C-band VV", icon: Satellite },
  { label: "Live feeds", value: "GFW · WDPA", sub: "+ Copernicus", icon: Globe2 },
  { label: "Reasoning", value: "Gemini 2.5", sub: "Flash agents", icon: Brain },
];

interface LandingPageProps {
  onLaunch: () => void;
  onDemo: () => void;
}

export default function LandingPage({ onLaunch, onDemo }: LandingPageProps) {
  const jumpTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-ocean-950 text-slate-200">
      <LandingNavbar items={navItems} onOpenDashboard={onLaunch} onJump={jumpTo} />

      <section
        id="hero"
        className="relative overflow-hidden px-4 pb-16 pt-32 md:px-6 md:pb-28 md:pt-36"
      >
        <div className="absolute inset-0 aurora-bg opacity-90" />
        <div className="absolute inset-0 ocean-grid opacity-35" />
        <div className="absolute inset-0 ocean-contours opacity-35" />
        <div className="absolute inset-0 radar-sweep opacity-30" />
        <div className="absolute left-[8%] top-28 h-44 w-44 rounded-full border border-cyan-300/10 bg-cyan-300/5 blur-2xl" />
        <div className="absolute right-[8%] top-48 h-56 w-56 rounded-full bg-teal-500/10 blur-[120px]" />
        <div className="absolute bottom-20 left-[32%] h-56 w-56 rounded-full bg-sky-500/10 blur-[140px]" />

        <div className="relative mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-300/15 bg-cyan-300/5 px-4 py-2 text-[11px] uppercase tracking-[0.24em] text-cyan-200/90"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_16px_rgba(34,211,238,0.85)]" />
            SDG 14 · Life Below Water
          </motion.div>

          <div className="max-w-4xl">
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, delay: 0.08, ease: EASE }}
              className="font-display text-[clamp(3.3rem,7vw,6.5rem)] leading-[0.98] tracking-[-0.04em] text-white"
            >
              Making hidden ocean activity visible with satellite AI
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, delay: 0.16, ease: EASE }}
              className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 md:text-xl"
            >
              Turn satellite vessel detections into clear evidence cards for faster human review.
            </motion.p>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.24, ease: EASE }}
              className="mt-5 max-w-xl text-sm leading-7 text-slate-400 md:text-base"
            >
              Built for maritime analysts, conservation teams, and protected-area monitoring.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, delay: 0.28, ease: EASE }}
              className="mt-10 flex flex-wrap items-center gap-4"
            >
              <GradientButton variant="primary" size="lg" onClick={onLaunch}>
                Open Dashboard <ArrowRight className="h-4 w-4" />
              </GradientButton>
              <GradientButton variant="secondary" size="lg" onClick={() => jumpTo("how-it-works")}>
                See How It Works
              </GradientButton>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="mt-10 flex flex-wrap gap-3"
            >
              {[
                "Sentinel-1 SAR",
                "AIS evidence comparison",
                "WDPA protected areas",
                "AI evidence cards",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-full border border-cyan-300/10 bg-ocean-900/65 px-4 py-2 text-xs text-slate-300 backdrop-blur-md"
                >
                  {item}
                </div>
              ))}
            </motion.div>
          </div>

          <div className="mt-16 md:mt-20">
            <DashboardPreview />
          </div>
        </div>
      </section>

      <section id="problem" className="px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.95fr_1.05fr]">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp}>
            <div className="mb-4 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-amber-300">
              <AlertTriangle className="h-4 w-4" />
              The challenge
            </div>
            <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
              The ocean is too large to monitor manually.
            </h2>
            <p className="mt-6 max-w-xl text-base leading-8 text-slate-400">
              Some vessels may not appear clearly in public tracking systems. Patrol and conservation teams need faster ways to identify which satellite detections deserve review.
            </p>
          </motion.div>

          <div className="grid gap-4 md:grid-cols-3">
            {problemCards.map((card, i) => {
              const Icon = card.icon;
              return (
                <motion.div key={card.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={i + 1} variants={fadeUp} className="rounded-[1.75rem] border border-cyan-300/10 bg-ocean-900/55 p-6 backdrop-blur-md">
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/10 bg-cyan-300/6">
                    <Icon className="h-5 w-5 text-cyan-300" />
                  </div>
                  <h3 className="font-display text-xl text-white">{card.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-400">{card.copy}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="technology" className="px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mx-auto max-w-3xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-300">
              <Sparkles className="h-4 w-4" />
              Solution
            </div>
            <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
              From satellite signal to evidence card.
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-slate-400">
              OceanGuard combines SAR detections, AIS comparison, protected-area context, and AI explanation into a clear analyst workflow.
            </p>
          </motion.div>

          <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {solutionCards.map((card, i) => {
              const Icon = card.icon;
              return (
                <motion.div key={card.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={i + 1} variants={fadeUp} className="group rounded-[1.75rem] border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(8,47,58,0.45),rgba(2,8,23,0.8))] p-6 transition-transform duration-300 hover:-translate-y-1">
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/10 bg-cyan-300/8 shadow-[0_0_30px_rgba(34,211,238,0.08)]">
                    <Icon className="h-5 w-5 text-cyan-300" />
                  </div>
                  <h3 className="font-display text-xl leading-7 text-white">{card.title}</h3>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="how-it-works" className="px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl">
          <ArchitectureGraph />
        </div>
      </section>

      <section id="workflow" className="relative overflow-hidden px-4 py-20 md:px-6 md:py-28">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(34,211,238,0.06),transparent_30%),radial-gradient(circle_at_85%_60%,rgba(20,184,166,0.06),transparent_30%)]" />
        <div className="relative mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mx-auto max-w-3xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-300">
              <Radar className="h-4 w-4" />
              Technical workflow
            </div>
            <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
              How a radar pulse becomes a reviewed case.
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-slate-400">
              Six stages, each running independently of vessel-reported tracking — so the system surfaces activity that
              transponder data alone would miss, and explains every step.
            </p>
          </motion.div>

          <div className="mt-14 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workflowSteps.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div
                  key={s.step}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, margin: "-80px" }}
                  custom={i + 1}
                  variants={fadeUp}
                  className="group relative overflow-hidden rounded-[1.75rem] border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(8,47,58,0.4),rgba(2,8,23,0.82))] p-6 transition-transform duration-300 hover:-translate-y-1"
                >
                  <div className="absolute right-5 top-4 font-display text-5xl font-bold text-cyan-300/10 transition-colors group-hover:text-cyan-300/20">
                    {s.step}
                  </div>
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/10 bg-cyan-300/8 shadow-[0_0_30px_rgba(34,211,238,0.08)]">
                    <Icon className="h-5 w-5 text-cyan-300" />
                  </div>
                  <h3 className="font-display text-xl leading-7 text-white">{s.title}</h3>
                  <div className="mt-2 inline-flex rounded-full border border-teal-400/15 bg-teal-400/5 px-3 py-1 text-[11px] font-medium text-teal-200/90">
                    {s.tech}
                  </div>
                  <p className="mt-4 text-sm leading-7 text-slate-400">{s.copy}</p>
                </motion.div>
              );
            })}
          </div>

          {/* Under-the-hood stat band */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            custom={1}
            variants={fadeUp}
            className="mt-12 rounded-[2rem] border border-cyan-300/10 bg-ocean-900/55 p-6 backdrop-blur-md md:p-8"
          >
            <div className="mb-6 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-slate-400">
              <Cpu className="h-4 w-4 text-cyan-300" />
              Under the hood
            </div>
            <div className="grid grid-cols-2 gap-y-8 md:grid-cols-3 xl:grid-cols-6">
              {techStack.map((t) => {
                const Icon = t.icon;
                return (
                  <div key={t.label} className="flex flex-col gap-1">
                    <Icon className="mb-1 h-4 w-4 text-cyan-300/70" />
                    <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{t.label}</div>
                    <div className="font-display text-lg text-white">{t.value}</div>
                    <div className="text-xs text-slate-400">{t.sub}</div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </div>
      </section>

      <section id="sdg-impact" className="relative overflow-hidden px-4 py-20 md:px-6 md:py-28">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,184,166,0.08),transparent_35%),radial-gradient(circle_at_80%_40%,rgba(14,165,233,0.08),transparent_32%)]" />
        <div className="absolute inset-0 ocean-contours opacity-25" />
        <div className="relative mx-auto max-w-7xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mx-auto max-w-3xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-teal-200">
              <Waves className="h-4 w-4" />
              Built for SDG 14
            </div>
            <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
              Built for SDG 14: Life Below Water
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-slate-400">
              OceanGuard supports responsible ocean monitoring by helping teams review vessel activity near protected marine areas and prioritize conservation attention.
            </p>
          </motion.div>

          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {impactCards.map((card, i) => {
              const Icon = card.icon;
              return (
                <motion.div key={card.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={i + 1} variants={fadeUp} className="rounded-[1.85rem] border border-teal-300/10 bg-ocean-900/55 p-6 backdrop-blur-md">
                  <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-teal-300/10 bg-teal-300/8">
                    <Icon className="h-5 w-5 text-teal-200" />
                  </div>
                  <h3 className="font-display text-xl text-white">{card.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-400">{card.copy}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="responsible-ai" className="px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-7xl rounded-[2rem] border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(6,24,38,0.92),rgba(2,8,23,0.98))] p-8 md:p-10">
          <div className="grid gap-10 lg:grid-cols-[0.95fr_1.05fr]">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp}>
              <div className="mb-4 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-amber-300">
                <Shield className="h-4 w-4" />
                Responsible AI
              </div>
              <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
                Decision support, not automatic accusation.
              </h2>
              <p className="mt-6 max-w-xl text-base leading-8 text-slate-400">
                OceanGuard flags possible risk signals and explains the evidence. Every output is designed for human verification before any action is taken.
              </p>
            </motion.div>

            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-1">
              {responsiblePrinciples.map((item, i) => {
                const Icon = item.icon;
                return (
                  <motion.div key={item.title} initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={i + 1} variants={fadeUp} className="flex items-center gap-4 rounded-[1.5rem] border border-cyan-300/10 bg-ocean-900/70 p-5">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/10 bg-cyan-300/8">
                      <Icon className="h-5 w-5 text-cyan-300" />
                    </div>
                    <div className="font-display text-lg text-white">{item.title}</div>
                  </motion.div>
                );
              })}
            </div>
          </div>

          <div className="mt-8 rounded-[1.5rem] border border-amber-300/10 bg-amber-300/5 px-5 py-4 text-sm leading-7 text-slate-300">
            OceanGuard does not accuse vessels. It supports human review with transparent evidence.
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 pt-6 md:px-6 md:pb-28">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-100px" }} custom={0} variants={fadeUp} className="mx-auto max-w-5xl rounded-[2.4rem] border border-cyan-300/10 bg-[linear-gradient(135deg,rgba(8,47,58,0.85),rgba(2,8,23,0.97))] px-6 py-10 text-center shadow-[0_24px_120px_rgba(8,47,58,0.35)] md:px-10 md:py-14">
          <div className="mx-auto max-w-3xl">
            <div className="mb-4 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-cyan-300">
              <Sparkles className="h-4 w-4" />
              Final call to action
            </div>
            <h2 className="font-display text-4xl leading-tight text-white md:text-5xl">
              Start reviewing ocean risk with satellite AI.
            </h2>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-slate-300">
              Open the live dashboard and explore how detections become evidence cards.
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

      <footer className="border-t border-ocean-700/30 px-4 py-8 md:px-6">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-3">
            <img src="/branding/oceanguard-mark.png" alt="OceanGuard AI" className="h-8 w-8 rounded-xl object-cover" />
            <div>
              <div className="font-display text-lg text-white">OceanGuard AI</div>
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Conservation intelligence</div>
            </div>
          </div>
          <div className="text-center text-sm text-slate-500 md:text-right">
            OceanGuard provides decision-support analysis. AI outputs must be verified by a human conservation officer before any enforcement action is taken.
          </div>
        </div>
      </footer>
    </div>
  );
}
