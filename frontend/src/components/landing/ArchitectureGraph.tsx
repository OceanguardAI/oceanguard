import React from "react";
import {
  ActivitySquare,
  ChevronRight,
  FileText,
  MapPinned,
  Radar,
  ScanSearch,
  ShieldCheck,
  ShipWheel,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { motion, Variants } from "framer-motion";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.1, ease: EASE },
  }),
};

type Step = { label: string; desc: string; icon: React.ComponentType<{ className?: string }> };
type Phase = { tag: string; title: string; accent: string; steps: Step[] };

// Three clear phases, left to right. Each phase lists its ordered steps, so the
// pipeline reads as a single flowing story instead of a scattered graph.
const PHASES: Phase[] = [
  {
    tag: "01 · Detect",
    title: "See the vessel",
    accent: "cyan",
    steps: [
      { label: "Sentinel-1 SAR", desc: "Raw ocean radar — works through cloud, day or night", icon: Radar },
      { label: "YOLO vessel detector", desc: "Our model finds ship-like returns in the radar", icon: ScanSearch },
      { label: "Detection coordinates", desc: "Each contact becomes a structured lat/lon event", icon: ActivitySquare },
    ],
  },
  {
    tag: "02 · Weigh",
    title: "Build the evidence",
    accent: "teal",
    steps: [
      { label: "AIS comparison", desc: "Cross-check against GFW + live AIS broadcasts", icon: ShipWheel },
      { label: "Protected-area check", desc: "Distance to the nearest WDPA marine reserve", icon: MapPinned },
      { label: "Risk scoring engine", desc: "Transparent score — AIS gap + MPA proximity", icon: ShieldCheck },
    ],
  },
  {
    tag: "03 · Explain",
    title: "Hand it to a human",
    accent: "sky",
    steps: [
      { label: "AI evidence writer", desc: "Plain-language narrative of why it was flagged", icon: Sparkles },
      { label: "Evidence card", desc: "A single review-ready case file per detection", icon: FileText },
      { label: "Human analyst review", desc: "An officer decides — the AI never accuses", icon: UserCheck },
    ],
  },
];

const ACCENT: Record<string, { text: string; chip: string; ring: string }> = {
  cyan: { text: "text-cyan-300", chip: "bg-cyan-300/8 border-cyan-300/15", ring: "border-cyan-300/12" },
  teal: { text: "text-teal-200", chip: "bg-teal-300/8 border-teal-300/15", ring: "border-teal-300/12" },
  sky:  { text: "text-sky-300",  chip: "bg-sky-300/8 border-sky-300/15",  ring: "border-sky-300/12" },
};

export default function ArchitectureGraph() {
  return (
    <div className="rounded-[2rem] border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(6,24,38,0.92),rgba(2,8,23,0.98))] p-5 shadow-[0_24px_100px_rgba(2,8,23,0.45)] md:p-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-cyan-300">How It Works</div>
          <div className="font-display text-2xl text-white md:text-3xl">From signal to evidence card</div>
        </div>
        <div className="rounded-full border border-cyan-300/10 bg-cyan-300/5 px-3 py-1 text-[11px] text-slate-400">
          Human review stays in the loop
        </div>
      </div>

      {/* Three phases, flowing left to right (stacked on mobile). */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {PHASES.map((phase, pi) => {
          const a = ACCENT[phase.accent];
          return (
            <React.Fragment key={phase.tag}>
              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-80px" }}
                custom={pi}
                variants={fadeUp}
                className={`flex-1 rounded-[1.6rem] border ${a.ring} bg-ocean-900/55 p-5 backdrop-blur-md`}
              >
                <div className={`mb-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${a.text}`}>
                  {phase.tag}
                </div>
                <div className="mb-5 font-display text-lg text-white">{phase.title}</div>

                <div className="space-y-3">
                  {phase.steps.map((step, si) => {
                    const Icon = step.icon;
                    return (
                      <div key={step.label} className="relative">
                        <div className="flex items-start gap-3 rounded-2xl border border-ocean-700/40 bg-ocean-950/50 p-3">
                          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${a.chip}`}>
                            <Icon className={`h-4 w-4 ${a.text}`} />
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-white">{step.label}</div>
                            <div className="mt-0.5 text-[11px] leading-relaxed text-slate-400">{step.desc}</div>
                          </div>
                        </div>
                        {/* Down-arrow between steps within a phase */}
                        {si < phase.steps.length - 1 && (
                          <div className="flex justify-center py-1">
                            <ChevronRight className={`h-3.5 w-3.5 rotate-90 ${a.text} opacity-50`} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </motion.div>

              {/* Arrow between phases: right on desktop, down on mobile */}
              {pi < PHASES.length - 1 && (
                <div className="flex items-center justify-center lg:px-1">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/15 bg-cyan-300/5">
                    <ChevronRight className="h-4 w-4 rotate-90 text-cyan-300 lg:rotate-0" />
                  </div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      <p className="mt-6 text-sm leading-relaxed text-slate-400">
        OceanGuard does not make enforcement decisions. It surfaces and explains evidence so a human
        officer can decide what deserves a closer look.
      </p>
    </div>
  );
}
