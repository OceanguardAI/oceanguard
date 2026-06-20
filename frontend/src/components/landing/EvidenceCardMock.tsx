import React from "react";
import { motion } from "framer-motion";
import { ScanSearch, Check, X } from "lucide-react";

const FIELDS = [
  { label: "SAR Detection", value: "CONFIRMED",     color: "text-cyan-300"  },
  { label: "AIS Signal",    value: "NO BROADCAST",  color: "text-red-400"   },
  { label: "MPA Proximity", value: "INSIDE ZONE",   color: "text-amber-300" },
  { label: "Est. Length",   value: "~84 m",         color: "text-slate-300" },
];

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

/** A polished mock of the product's signature output — a review-ready evidence card. */
export default function EvidenceCardMock() {
  return (
    <div className="relative mx-auto w-full max-w-sm">
      {/* ambient glow */}
      <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-cyan-400/10 blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: EASE }}
        className="overflow-hidden rounded-2xl border border-white/10 bg-[#04101a]/95 shadow-[0_30px_90px_rgba(0,0,0,0.6)] backdrop-blur-xl"
      >
        {/* gradient accent bar */}
        <div className="h-[3px] bg-gradient-to-r from-cyan-400 via-teal-400 to-amber-400" />

        <div className="p-5">
          {/* header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" style={{ animation: "blink 1.6s ease-in-out infinite" }} />
              CASE · GFW-SAR-0042
            </div>
            <div className="rounded-md border border-red-500/30 bg-red-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-red-400">
              CRITICAL
            </div>
          </div>

          {/* radar thumbnail */}
          <div className="relative mt-4 h-28 overflow-hidden rounded-xl border border-white/8" style={{ background: "radial-gradient(ellipse at 50% 45%, #06202e, #030c14 75%)" }}>
            <svg className="absolute inset-0 h-full w-full" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="ev-grid" width="22" height="22" patternUnits="userSpaceOnUse">
                  <path d="M22 0H0V22" fill="none" stroke="rgba(56,189,248,0.07)" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#ev-grid)" />
            </svg>
            {/* vessel blob + crosshair */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
              <span className="absolute rounded-full border border-red-400/40" style={{ inset: -12, animation: "vesselPulse 2.6s ease-out infinite" }} />
              <span className="block h-3 w-3 rounded-full bg-red-400 shadow-[0_0_12px_rgba(248,113,113,0.8)]" />
            </div>
            <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-red-400/15" />
            <span className="absolute top-1/2 left-0 w-full h-px -translate-y-1/2 bg-red-400/15" />
            <div className="absolute left-2 top-2 font-mono text-[8px] uppercase tracking-widest text-cyan-200/50">SENTINEL-1 · VV</div>
            <div className="absolute right-2 bottom-2 rounded border border-red-500/20 bg-[#0a0404]/80 px-1 py-px font-mono text-[8px] text-red-300/90">DARK VESSEL</div>
          </div>

          {/* fields */}
          <div className="mt-4 space-y-px">
            {FIELDS.map((f) => (
              <div key={f.label} className="flex items-center justify-between border-b border-white/[0.05] py-1.5 last:border-0">
                <span className="text-[11px] text-slate-500">{f.label}</span>
                <span className={`font-mono text-[11px] ${f.color}`}>{f.value}</span>
              </div>
            ))}
          </div>

          {/* risk meter */}
          <div className="mt-4">
            <div className="mb-1.5 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.16em]">
              <span className="text-slate-500">Risk score</span>
              <span className="text-red-400">0.91</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: "91%" }}
                viewport={{ once: true }}
                transition={{ delay: 0.4, duration: 0.9, ease: EASE }}
                className="h-full rounded-full bg-gradient-to-r from-amber-400 to-red-500"
              />
            </div>
          </div>

          {/* actions */}
          <div className="mt-5 flex items-center gap-2">
            <button className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-gradient-to-r from-teal-600 to-teal-400 py-2 text-xs font-semibold text-white">
              <Check className="h-3.5 w-3.5" /> Confirm
            </button>
            <button className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-white/12 py-2 text-xs font-semibold text-slate-300">
              <X className="h-3.5 w-3.5" /> Dismiss
            </button>
          </div>
          <button className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.06] py-2 text-xs font-semibold text-cyan-300">
            <ScanSearch className="h-3.5 w-3.5" /> Run YOLO Check ›
          </button>
        </div>
      </motion.div>
    </div>
  );
}
