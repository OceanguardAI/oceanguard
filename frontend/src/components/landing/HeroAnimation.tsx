import React from "react";
import { motion } from "framer-motion";

// Fictional vessel positions — some dark (red), some normal (cyan).
const VESSELS = [
  { x: 24, y: 40, dark: true,  delay: 1.0 },
  { x: 43, y: 26, dark: false, delay: 1.7 },
  { x: 63, y: 49, dark: true,  delay: 2.4 },
  { x: 77, y: 36, dark: true,  delay: 3.0 },
  { x: 37, y: 66, dark: false, delay: 2.7 },
  { x: 18, y: 57, dark: true,  delay: 3.4 },
];

const CARD_ROWS = [
  { label: "SAR Detection",  value: "CONFIRMED",    color: "#22d3ee" },
  { label: "AIS Signal",     value: "NO BROADCAST", color: "#f87171" },
  { label: "MPA Proximity",  value: "INSIDE ZONE",  color: "#fbbf24" },
  { label: "Human Review",   value: "PENDING →",    color: "#94a3b8" },
];

export default function HeroAnimation() {
  return (
    <div
      className="relative w-full overflow-hidden rounded-2xl border border-white/8 shadow-[0_32px_90px_rgba(0,0,0,0.75)]"
      style={{ paddingBottom: "72%", background: "linear-gradient(155deg, #020C14 0%, #041520 55%, #020A10 100%)" }}
    >
      <div className="absolute inset-0">

        {/* ── Grid + bathymetry contours + vignette ── */}
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 800 576"
          preserveAspectRatio="xMidYMid slice"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <pattern id="og-grid" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M60 0H0V60" fill="none" stroke="rgba(6,182,212,0.07)" strokeWidth="0.5" />
            </pattern>
            <radialGradient id="og-vignette" cx="50%" cy="50%" r="55%">
              <stop offset="0%"   stopColor="black" stopOpacity="0" />
              <stop offset="100%" stopColor="black" stopOpacity="0.72" />
            </radialGradient>
          </defs>
          <rect width="800" height="576" fill="url(#og-grid)" />

          {/* Bathymetry depth contours */}
          <path d="M0,155 C130,138 300,162 470,146 T800,155"    stroke="rgba(6,182,212,0.09)" fill="none" strokeWidth="1.5" />
          <path d="M0,245 C160,228 330,250 500,233 T800,243"    stroke="rgba(6,182,212,0.07)" fill="none" strokeWidth="1"   />
          <path d="M0,335 C180,318 360,340 540,322 T800,332"    stroke="rgba(6,182,212,0.06)" fill="none" strokeWidth="1"   />
          <path d="M0,420 C200,406 390,425 580,410 T800,418"    stroke="rgba(6,182,212,0.05)" fill="none" strokeWidth="0.7" />
          <path d="M100,0 C115,130 95,290 110,400 S100,510 105,576" stroke="rgba(6,182,212,0.04)" fill="none" strokeWidth="0.5" />
          <path d="M370,0 C355,110 375,260 358,380 S372,490 365,576" stroke="rgba(6,182,212,0.03)" fill="none" strokeWidth="0.5" />

          <rect width="800" height="576" fill="url(#og-vignette)" />
        </svg>

        {/* ── Radar rings expanding from center-ish ── */}
        {[0, 1, 2].map((i) => {
          const size = 130 + i * 90;
          return (
            <div
              key={i}
              className="absolute rounded-full border border-cyan-400/20"
              style={{
                width: size,
                height: size,
                left: `calc(44% - ${size / 2}px)`,
                top:  `calc(47% - ${size / 2}px)`,
                animation: `radarRing 4.5s ease-out ${i * 1.4}s infinite`,
              }}
            />
          );
        })}

        {/* ── Satellite scan sweep line ── */}
        <div
          className="absolute inset-y-0 w-px pointer-events-none"
          style={{
            background:
              "linear-gradient(to bottom, transparent 5%, rgba(34,211,238,0.45) 35%, rgba(34,211,238,0.85) 50%, rgba(34,211,238,0.45) 65%, transparent 95%)",
            boxShadow: "0 0 22px 10px rgba(34,211,238,0.09)",
            animation: "scanLine 5.5s linear 0.5s infinite",
          }}
        />

        {/* ── Vessel detection dots ── */}
        {VESSELS.map((v, i) => (
          <motion.div
            key={i}
            className="absolute"
            style={{ left: `${v.x}%`, top: `${v.y}%`, transform: "translate(-50%,-50%)" }}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: v.delay, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Pulse ring for dark vessels */}
            {v.dark && (
              <div
                className="absolute rounded-full border border-red-400/40"
                style={{ inset: "-10px", animation: "vesselPulse 2.5s ease-out 0s infinite" }}
              />
            )}
            {/* Dot */}
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                v.dark
                  ? "bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.65)]"
                  : "bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.55)]"
              }`}
            />
            {/* DARK label */}
            {v.dark && (
              <div className="absolute left-4 top-1/2 -translate-y-1/2 whitespace-nowrap font-mono text-[9px] text-red-400/90 bg-[#080404]/80 px-1.5 py-0.5 rounded border border-red-500/20">
                DARK
              </div>
            )}
          </motion.div>
        ))}

        {/* ── Evidence card (slides in after initial scan pass) ── */}
        <div className="absolute right-4 top-1/2 -translate-y-1/2">
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 4.2, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            style={{
              width: 192,
              background: "rgba(4,10,16,0.90)",
              backdropFilter: "blur(20px)",
              WebkitBackdropFilter: "blur(20px)",
              border: "1px solid rgba(255,255,255,0.10)",
              borderRadius: 14,
            }}
          >
            {/* Gradient accent bar */}
            <div style={{ height: 2, background: "linear-gradient(90deg,rgba(34,211,238,0.6),rgba(251,191,36,0.55))", borderRadius: "14px 14px 0 0" }} />

            <div style={{ padding: "10px 12px" }}>
              {/* Header */}
              <div className="flex items-center gap-1.5 mb-2.5">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                <span className="font-mono text-[9px] uppercase tracking-widest text-amber-300/75">
                  gfw-sar-0042
                </span>
              </div>

              {/* Field rows */}
              {CARD_ROWS.map((row, ri) => (
                <div
                  key={ri}
                  className="flex items-center justify-between py-1 border-b border-white/[0.05] last:border-0"
                >
                  <span className="text-[10px] text-slate-500">{row.label}</span>
                  <span className="font-mono text-[10px]" style={{ color: row.color }}>
                    {row.value}
                  </span>
                </div>
              ))}

              {/* Action button */}
              <div
                style={{
                  marginTop: 10,
                  padding: "6px 0",
                  textAlign: "center",
                  fontSize: 10,
                  fontWeight: 600,
                  color: "white",
                  background: "linear-gradient(90deg,rgba(6,182,212,0.65),rgba(20,184,166,0.65))",
                  borderRadius: 8,
                }}
              >
                Run YOLO Check ›
              </div>
            </div>
          </motion.div>
        </div>

        {/* ── Corner metadata labels ── */}
        <div className="absolute top-3 left-3 font-mono text-[10px] text-cyan-400/35">
          54.5600°N · 11.0700°E
        </div>
        <div className="absolute bottom-3 right-3 flex items-center gap-1.5 font-mono text-[10px] text-slate-700">
          <span className="w-1 h-1 rounded-full bg-cyan-400 animate-pulse" />
          SENTINEL-1 · LIVE
        </div>

      </div>
    </div>
  );
}
