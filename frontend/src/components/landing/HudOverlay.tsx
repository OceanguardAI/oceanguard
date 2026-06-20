import React from "react";

/**
 * Surveillance HUD that frames the hero video like a live satellite feed:
 * corner brackets, coordinate readouts, a REC indicator and a scan sweep.
 * Purely decorative — pointer-events-none so the hero buttons stay clickable.
 */
export default function HudOverlay() {
  return (
    <div className="pointer-events-none absolute inset-0 z-20 select-none">

      {/* ── Corner brackets ── */}
      <span className="absolute left-4 top-4  h-7 w-7 border-l-2 border-t-2 border-cyan-300/45 md:left-7 md:top-7" />
      <span className="absolute right-4 top-4 h-7 w-7 border-r-2 border-t-2 border-cyan-300/45 md:right-7 md:top-7" />
      <span className="absolute left-4 bottom-4  h-7 w-7 border-l-2 border-b-2 border-cyan-300/45 md:left-7 md:bottom-7" />
      <span className="absolute right-4 bottom-4 h-7 w-7 border-r-2 border-b-2 border-cyan-300/45 md:right-7 md:bottom-7" />

      {/* ── Top-left: REC + sensor ── */}
      <div className="absolute left-7 top-7 hidden items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200/70 md:flex">
        <span className="h-2 w-2 rounded-full bg-red-500" style={{ animation: "blink 1.4s ease-in-out infinite" }} />
        REC
        <span className="text-cyan-200/25">·</span>
        SENTINEL-1 SAR
      </div>

      {/* ── Top-right: coordinates ── */}
      <div className="absolute right-7 top-7 hidden font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200/55 md:block">
        54.56°N · 11.07°E
      </div>

      {/* ── Bottom-left: scan status ── */}
      <div className="absolute left-7 bottom-7 hidden items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-amber-300/70 md:flex">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" style={{ animation: "blink 2s ease-in-out infinite" }} />
        SCAN MODE · ACTIVE
      </div>

      {/* ── Center reticle ── */}
      <span className="absolute left-1/2 top-1/2 h-8 w-px -translate-x-1/2 -translate-y-1/2 bg-cyan-300/15" />
      <span className="absolute left-1/2 top-1/2 h-px w-8 -translate-x-1/2 -translate-y-1/2 bg-cyan-300/15" />

      {/* ── Horizontal scan sweep ── */}
      <div
        className="absolute inset-x-0 h-[2px]"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(34,211,238,0.55) 35%, rgba(34,211,238,0.55) 65%, transparent)",
          boxShadow: "0 0 18px 2px rgba(34,211,238,0.18)",
          animation: "hudScan 8s linear infinite",
        }}
      />
    </div>
  );
}
