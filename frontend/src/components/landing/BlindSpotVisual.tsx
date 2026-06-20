import React from "react";
import { motion } from "framer-motion";

// Three vessels that publicly broadcast (shown on BOTH panels).
const BROADCASTING = [
  { x: 30, y: 36 },
  { x: 63, y: 56 },
  { x: 47, y: 75 },
];

// Nine "dark" vessels — invisible to public tracking, revealed only by radar.
const DARK = [
  { x: 18, y: 60 }, { x: 40, y: 22 }, { x: 55, y: 40 },
  { x: 72, y: 28 }, { x: 80, y: 63 }, { x: 25, y: 82 },
  { x: 67, y: 80 }, { x: 38, y: 52 }, { x: 86, y: 44 },
];

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

function Grid() {
  return (
    <svg className="absolute inset-0 h-full w-full" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="bs-grid" width="34" height="34" patternUnits="userSpaceOnUse">
          <path d="M34 0H0V34" fill="none" stroke="rgba(56,189,248,0.06)" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#bs-grid)" />
    </svg>
  );
}

function Dot({ x, y, dark, delay, withSweepLabel }: { x: number; y: number; dark?: boolean; delay: number; withSweepLabel?: boolean }) {
  return (
    <motion.div
      className="absolute -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${x}%`, top: `${y}%` }}
      initial={{ opacity: 0, scale: 0 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.3, ease: EASE }}
    >
      {dark && (
        <span
          className="absolute rounded-full border border-red-400/40"
          style={{ inset: -8, animation: "vesselPulse 2.6s ease-out infinite" }}
        />
      )}
      <span
        className={`block rounded-full ${
          dark
            ? "h-2.5 w-2.5 bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.7)]"
            : "h-2.5 w-2.5 bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.6)]"
        }`}
      />
      {withSweepLabel && (
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 whitespace-nowrap rounded border border-red-500/20 bg-[#0a0404]/85 px-1 py-px font-mono text-[8px] text-red-300/90">
          DARK
        </span>
      )}
    </motion.div>
  );
}

function Panel({
  kind,
  count,
  countLabel,
  caption,
  children,
}: {
  kind: "ais" | "sar";
  count: string;
  countLabel: string;
  caption: string;
  children: React.ReactNode;
}) {
  const accent = kind === "sar" ? "text-amber-300" : "text-cyan-300";
  const dotColor = kind === "sar" ? "bg-amber-400" : "bg-cyan-300";
  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/8 bg-[#04101a]">
      {/* corner ticks */}
      <span className="absolute left-2.5 top-2.5 h-3.5 w-3.5 border-l border-t border-white/20" />
      <span className="absolute right-2.5 top-2.5 h-3.5 w-3.5 border-r border-t border-white/20" />
      <span className="absolute left-2.5 bottom-2.5 h-3.5 w-3.5 border-l border-b border-white/20" />
      <span className="absolute right-2.5 bottom-2.5 h-3.5 w-3.5 border-r border-b border-white/20" />

      {/* header */}
      <div className="flex items-center justify-between px-4 pt-3.5">
        <div className={`flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] ${accent}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} style={{ animation: "blink 2s ease-in-out infinite" }} />
          {kind === "sar" ? "SAR · SATELLITE RADAR" : "AIS · PUBLIC TRACKING"}
        </div>
      </div>

      {/* radar field */}
      <div className="relative mx-4 my-3 aspect-[4/3] overflow-hidden rounded-xl" style={{ background: "radial-gradient(ellipse at 50% 40%, #06202e, #030c14 75%)" }}>
        <Grid />
        {kind === "sar" && (
          <div
            className="absolute left-1/2 top-1/2 h-[140%] w-[140%] -translate-x-1/2 -translate-y-1/2"
            style={{
              background: "conic-gradient(from 0deg, rgba(251,191,36,0.16), transparent 30%, transparent 100%)",
              animation: "sweep 6s linear infinite",
            }}
          />
        )}
        {children}
      </div>

      {/* count + caption */}
      <div className="flex items-end justify-between px-4 pb-4">
        <div>
          <div className={`font-mono text-3xl font-bold ${accent}`}>{count}</div>
          <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-500">{countLabel}</div>
        </div>
        <p className="max-w-[55%] text-right text-[11px] leading-4 text-slate-500">{caption}</p>
      </div>
    </div>
  );
}

export default function BlindSpotVisual() {
  return (
    <div>
      <div className="grid gap-4 md:grid-cols-2">
        {/* AIS — only broadcasting vessels */}
        <Panel
          kind="ais"
          count="03"
          countLabel="vessels visible"
          caption="What the world can see today."
        >
          {BROADCASTING.map((v, i) => (
            <Dot key={i} {...v} delay={0.15 + i * 0.12} />
          ))}
        </Panel>

        {/* SAR — everything */}
        <Panel
          kind="sar"
          count="12"
          countLabel="vessels detected"
          caption="What the radar actually sees."
        >
          {BROADCASTING.map((v, i) => (
            <Dot key={`b${i}`} {...v} delay={0.15 + i * 0.12} />
          ))}
          {DARK.map((v, i) => (
            <Dot key={`d${i}`} {...v} dark delay={0.7 + i * 0.1} withSweepLabel={i === 0} />
          ))}
        </Panel>
      </div>

      {/* the line that makes the point */}
      <motion.p
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.4, duration: 0.5 }}
        className="mx-auto mt-6 max-w-xl text-center text-base leading-7 text-slate-300"
      >
        Public tracking shows <span className="font-semibold text-cyan-300">3 vessels</span>.
        Satellite radar reveals <span className="font-semibold text-amber-300">12</span>.
        The other <span className="font-semibold text-red-400">9 switched their transponders off</span> — and disappeared.
      </motion.p>
    </div>
  );
}
