import React, { useRef, useState } from "react";
import { motion, Variants } from "framer-motion";
import {
  AlertTriangle, ArrowRight, ChevronDown,
  FileText, Satellite, ScanSearch, ShieldCheck, Volume2, VolumeX,
} from "lucide-react";
import GradientButton from "./ui/GradientButton";
import HeroAnimation from "./landing/HeroAnimation";
import HudOverlay from "./landing/HudOverlay";
import BlindSpotVisual from "./landing/BlindSpotVisual";
import LandingNavbar from "./landing/LandingNavbar";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];
const fadeUp: Variants = {
  hidden: { opacity: 0, y: 22 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.55, delay: i * 0.09, ease: EASE },
  }),
};

const navItems = [
  { label: "The Blind Spot", target: "problem"  },
  { label: "The System",     target: "solution" },
];

const TICKER = [
  "⬤  LIVE SYSTEM ACTIVE",
  "Sentinel-1 radar · global ocean coverage",
  "Global Fishing Watch · live SAR detections",
  "WDPA · 10 000+ marine protected areas indexed",
  "YOLO11n detection model · mAP@50 0.838",
  "AI evidence cards · human review required",
];

const STAKES = [
  { value: "$23B",    label: "lost to illegal fishing / yr" },
  { value: "1 in 5",  label: "fish caught outside the rules" },
  { value: "Hours",   label: "to act — not days" },
];

const STAGES = [
  { no: "01", tag: "ACQUIRE", icon: Satellite,    title: "Global radar passes", copy: "Sentinel-1 SAR images the ocean day and night, straight through cloud cover.",      accent: "text-cyan-300",  ring: "border-cyan-300/25" },
  { no: "02", tag: "DETECT",  icon: ScanSearch,   title: "AI finds every contact", copy: "YOLO11n scans the raw radar and flags every vessel — broadcasting or dark.",        accent: "text-cyan-300",  ring: "border-cyan-300/25" },
  { no: "03", tag: "SCORE",   icon: AlertTriangle,title: "Risk gets ranked",      copy: "A dark vessel inside a protected zone scores highest. The queue sorts itself.",      accent: "text-amber-300", ring: "border-amber-300/25" },
  { no: "04", tag: "REVIEW",  icon: FileText,     title: "An officer decides",    copy: "Each contact becomes an evidence card. A human confirms before any action is taken.", accent: "text-teal-300",  ring: "border-teal-300/25" },
];

const HERO_VIDEO_SRC = "/hero-video.mp4";

interface Props { onLaunch: () => void; onDemo: () => void; }

/** Editorial numbered section label: 01 ──── THE BLIND SPOT */
function SectionTag({ no, label, accent }: { no: string; label: string; accent: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className={`font-mono text-sm font-bold ${accent}`}>{no}</span>
      <span className={`h-px w-10 ${accent.replace("text-", "bg-")} opacity-40`} />
      <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-slate-400">{label}</span>
    </div>
  );
}

export default function LandingPage({ onLaunch, onDemo }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [muted, setMuted] = useState(true);
  const [videoReady, setVideoReady] = useState(false);

  const jumpTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !muted;
    setMuted((v) => !v);
  };

  return (
    <div className="min-h-screen overflow-x-hidden text-slate-200" style={{ background: "#040C11" }}>

      {/* ── Live ticker ── */}
      <div className="relative overflow-hidden border-b border-amber-400/15 bg-amber-400/[0.04] py-1.5">
        <div className="flex items-center gap-10 whitespace-nowrap" style={{ animation: "ticker 50s linear infinite", willChange: "transform" }}>
          {[...TICKER, ...TICKER].map((item, i) => (
            <span key={i} className="flex shrink-0 items-center gap-3">
              {i % TICKER.length === 0
                ? <span className="font-mono text-[11px] font-bold text-amber-400">{item}</span>
                : <><span className="text-amber-400/20">│</span><span className="font-mono text-[11px] text-amber-200/50">{item}</span></>}
            </span>
          ))}
        </div>
      </div>

      <LandingNavbar items={navItems} onOpenDashboard={onLaunch} onJump={jumpTo} />

      {/* ══════════════════════════════════════════
          HERO — satellite feed (video + HUD frame)
      ══════════════════════════════════════════ */}
      <section id="hero" className="relative h-[100svh] min-h-[600px] overflow-hidden">

        {/* Video */}
        <video
          ref={videoRef}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${videoReady ? "opacity-100" : "opacity-0"}`}
          src={HERO_VIDEO_SRC}
          autoPlay muted loop playsInline
          onCanPlay={() => setVideoReady(true)}
        />

        {/* Fallback animation until video is ready */}
        {!videoReady && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#040C11]">
            <div className="w-full max-w-2xl px-4"><HeroAnimation /></div>
          </div>
        )}

        {/* Readability overlays */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/55 via-black/25 to-black/80" />
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse 75% 65% at 50% 46%, rgba(2,8,12,0.42), transparent 78%)" }} />

        {/* Surveillance HUD frame */}
        <HudOverlay />

        {/* Centered content */}
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center px-6 text-center">
          <div className="max-w-4xl">
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.2 }}
              className="mb-6 flex items-center justify-center gap-2.5"
            >
              <span className="h-2.5 w-2.5 rounded-[3px] bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.7)]" />
              <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-amber-300">
                SDG 14 · Satellite Intelligence
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.65, delay: 0.3, ease: EASE }}
              className="font-display font-black text-white leading-[0.96] tracking-[-0.04em]"
              style={{ fontSize: "clamp(2.8rem, 6vw, 6.5rem)", textShadow: "0 2px 40px rgba(0,0,0,0.55)" }}
            >
              Making hidden ocean<br />
              activity <span className="text-amber-400">visible</span>.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55, delay: 0.45, ease: EASE }}
              className="mx-auto mt-6 max-w-xl text-base leading-7 text-white/75 md:text-lg"
              style={{ textShadow: "0 1px 20px rgba(0,0,0,0.6)" }}
            >
              Satellite radar catches vessels that switch their tracking off.
              OceanGuard turns those detections into reviewed evidence cards — in minutes.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.56, ease: EASE }}
              className="mt-9 flex flex-wrap items-center justify-center gap-3"
            >
              <GradientButton variant="primary" size="lg" onClick={onLaunch}>
                Open Dashboard <ArrowRight className="h-4 w-4" />
              </GradientButton>
              <GradientButton variant="secondary" size="lg" onClick={() => jumpTo("problem")}>
                See the Problem
              </GradientButton>
            </motion.div>
          </div>
        </div>

        {/* Mute toggle */}
        {videoReady && (
          <button
            onClick={toggleMute}
            className="absolute bottom-6 right-6 z-30 flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-black/40 text-white/70 backdrop-blur-sm transition hover:border-white/40 hover:text-white"
            aria-label={muted ? "Unmute" : "Mute"}
          >
            {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        )}

        {/* Scroll hint */}
        <motion.button
          onClick={() => jumpTo("problem")}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.6 }}
          className="absolute bottom-6 left-1/2 z-30 flex -translate-x-1/2 flex-col items-center gap-1 text-white/40 transition hover:text-white/70"
          aria-label="Scroll down"
        >
          <span className="font-mono text-[9px] uppercase tracking-[0.2em]">Scroll</span>
          <ChevronDown className="h-4 w-4 animate-bounce" />
        </motion.button>
      </section>

      {/* ══════════════════════════════════════════
          01 — THE BLIND SPOT  (problem)
      ══════════════════════════════════════════ */}
      <section id="problem" className="relative border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        <div className="mx-auto max-w-5xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}>
            <SectionTag no="01" label="The Blind Spot" accent="text-amber-400" />
            <h2 className="mt-5 max-w-2xl font-display text-4xl font-black leading-tight text-white md:text-5xl">
              Most of the ocean is a blind spot.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-8 text-slate-400">
              Vessels that want to stay hidden simply switch off their transponders.
              Public tracking loses them instantly. Radar does not.
            </p>
          </motion.div>

          {/* The contrast visual — the whole argument in one picture */}
          <motion.div
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={1} variants={fadeUp}
            className="mt-12"
          >
            <BlindSpotVisual />
          </motion.div>

          {/* Stakes */}
          <motion.div
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={2} variants={fadeUp}
            className="mt-14 grid grid-cols-3 gap-4 border-t border-white/8 pt-8"
          >
            {STAKES.map((s) => (
              <div key={s.label} className="text-center md:text-left">
                <div className="font-mono text-2xl font-bold text-white md:text-3xl">{s.value}</div>
                <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-slate-500">{s.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          02 — THE SYSTEM  (solution pipeline)
      ══════════════════════════════════════════ */}
      <section id="solution" className="relative border-t border-white/6 px-4 py-20 md:px-6 md:py-28">
        {/* faint chart grid texture */}
        <div className="pointer-events-none absolute inset-0 opacity-[0.4] ocean-grid" />

        <div className="relative mx-auto max-w-6xl">
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}>
            <SectionTag no="02" label="The System" accent="text-cyan-400" />
            <h2 className="mt-5 max-w-2xl font-display text-4xl font-black leading-tight text-white md:text-5xl">
              From raw radar to a reviewed case — in four steps.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-8 text-slate-400">
              A single pipeline does the watching, the ranking and the explaining.
              People stay in charge of the deciding.
            </p>
          </motion.div>

          {/* Pipeline */}
          <div className="relative mt-14 grid gap-8 md:grid-cols-4 md:gap-5">
            {/* connecting rail (desktop) */}
            <div className="absolute left-0 right-0 top-7 hidden h-px bg-gradient-to-r from-cyan-400/30 via-teal-400/30 to-amber-400/30 md:block" />

            {STAGES.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div
                  key={s.no}
                  initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={i + 1} variants={fadeUp}
                  className="relative"
                >
                  <div className={`relative z-10 mb-5 flex h-14 w-14 items-center justify-center rounded-xl border ${s.ring} bg-[#040c11]`}>
                    <Icon className={`h-5 w-5 ${s.accent}`} />
                  </div>
                  <div className={`font-mono text-[10px] uppercase tracking-[0.22em] ${s.accent}`}>
                    {s.no} · {s.tag}
                  </div>
                  <div className="mt-1.5 font-display text-lg font-semibold text-white">{s.title}</div>
                  <p className="mt-1.5 text-sm leading-6 text-slate-400">{s.copy}</p>
                </motion.div>
              );
            })}
          </div>

          {/* Responsible-AI line */}
          <motion.div
            initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-60px" }} custom={1} variants={fadeUp}
            className="mt-16 flex items-start gap-3 rounded-2xl border border-teal-400/15 bg-teal-400/[0.04] p-5"
          >
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-teal-300" />
            <p className="text-sm leading-7 text-slate-300">
              <span className="font-semibold text-white">OceanGuard never accuses.</span>{" "}
              It surfaces evidence and explains it in plain language. Every case is reviewed by a
              human officer before any enforcement action — the AI advises, people decide.
            </p>
          </motion.div>
        </div>
      </section>

      {/* ══════════════════════════════════════════
          CTA
      ══════════════════════════════════════════ */}
      <section className="px-4 pb-24 pt-4 md:px-6">
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true, margin: "-80px" }} custom={0} variants={fadeUp}
          className="relative mx-auto max-w-4xl overflow-hidden rounded-2xl border border-white/10 bg-[#040C11]"
        >
          {/* corner brackets — echo the hero HUD */}
          <span className="absolute left-3 top-3 h-5 w-5 border-l-2 border-t-2 border-amber-400/40" />
          <span className="absolute right-3 top-3 h-5 w-5 border-r-2 border-t-2 border-amber-400/40" />
          <span className="absolute left-3 bottom-3 h-5 w-5 border-l-2 border-b-2 border-amber-400/40" />
          <span className="absolute right-3 bottom-3 h-5 w-5 border-r-2 border-b-2 border-amber-400/40" />

          <div className="px-8 py-14 text-center md:px-10 md:py-16">
            <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-amber-400/25 bg-amber-400/8 px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-amber-300">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" style={{ animation: "blink 1.6s ease-in-out infinite" }} />
              System active
            </div>
            <h2 className="font-display text-4xl font-black text-white md:text-5xl">
              See the vessels that<br className="hidden md:block" /> don't want to be seen.
            </h2>
            <p className="mx-auto mt-5 max-w-lg text-base leading-8 text-slate-400">
              Open the live console — real satellite detections, AI evidence cards, human review built in.
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
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 md:flex-row">
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
