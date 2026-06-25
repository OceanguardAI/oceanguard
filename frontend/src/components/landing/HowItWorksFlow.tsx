import React from "react";
import { motion } from "framer-motion";
import { Satellite, ScanSearch, AlertTriangle, FileText } from "lucide-react";

const STEPS = [
  {
    no: "01",
    icon: Satellite,
    title: "SAR Satellite",
    sub: "Radar images\nthe ocean",
    accent: "#22d3ee",
    glow: "rgba(34,211,238,0.18)",
  },
  {
    no: "02",
    icon: ScanSearch,
    title: "AI Detection",
    sub: "Every vessel\nflagged",
    accent: "#22d3ee",
    glow: "rgba(34,211,238,0.18)",
  },
  {
    no: "03",
    icon: AlertTriangle,
    title: "Risk Scoring",
    sub: "Dark vessels\nranked first",
    accent: "#fbbf24",
    glow: "rgba(251,191,36,0.18)",
  },
  {
    no: "04",
    icon: FileText,
    title: "Evidence Card",
    sub: "Human reviews\n& decides",
    accent: "#2dd4bf",
    glow: "rgba(45,212,191,0.18)",
  },
];

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

export default function HowItWorksFlow() {
  return (
    <div className="w-full">
      {/* heading */}
      <div className="mb-14 text-center">
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: EASE }}
          className="font-display text-4xl font-black text-white md:text-5xl"
        >
          How It{" "}
          <span style={{ color: "#22d3ee", textShadow: "0 0 40px rgba(34,211,238,0.4)" }}>
            Works
          </span>
        </motion.h2>
        {/* teal underline accent — echoes the YouTube reference */}
        <motion.div
          initial={{ scaleX: 0 }} whileInView={{ scaleX: 1 }}
          viewport={{ once: true }} transition={{ delay: 0.25, duration: 0.55, ease: EASE }}
          className="mx-auto mt-3 h-[3px] w-20 origin-left rounded-full"
          style={{ background: "linear-gradient(90deg,#22d3ee,transparent)" }}
        />
      </div>

      {/* flow row */}
      <div className="flex flex-col items-center gap-6 md:flex-row md:items-start md:justify-center md:gap-0">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <React.Fragment key={step.no}>
              {/* Step box */}
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ delay: i * 0.13, duration: 0.5, ease: EASE }}
                className="flex flex-col items-center gap-3"
                style={{ minWidth: 140 }}
              >
                {/* step number */}
                <span
                  className="font-mono text-[11px] font-bold uppercase tracking-[0.22em]"
                  style={{ color: step.accent }}
                >
                  {step.no}
                </span>

                {/* label above box */}
                <span className="font-display text-[15px] font-semibold text-white">
                  {step.title}
                </span>

                {/* icon box */}
                <div
                  className="relative flex h-[88px] w-[88px] items-center justify-center rounded-2xl md:h-[100px] md:w-[100px]"
                  style={{
                    background: "rgba(6,18,30,0.9)",
                    border: `1.5px solid ${step.accent}40`,
                    boxShadow: `0 0 32px ${step.glow}, inset 0 1px 0 rgba(255,255,255,0.06)`,
                  }}
                >
                  {/* corner ticks */}
                  <span className="absolute left-2 top-2 h-2.5 w-2.5 border-l border-t" style={{ borderColor: `${step.accent}60` }} />
                  <span className="absolute right-2 top-2 h-2.5 w-2.5 border-r border-t" style={{ borderColor: `${step.accent}60` }} />
                  <span className="absolute left-2 bottom-2 h-2.5 w-2.5 border-l border-b" style={{ borderColor: `${step.accent}60` }} />
                  <span className="absolute right-2 bottom-2 h-2.5 w-2.5 border-r border-b" style={{ borderColor: `${step.accent}60` }} />

                  <Icon className="h-9 w-9 md:h-10 md:w-10" style={{ color: step.accent, filter: `drop-shadow(0 0 8px ${step.accent}80)` }} />
                </div>

                {/* sub label below box */}
                <p className="text-center font-mono text-[11px] leading-5 tracking-[0.06em] text-slate-400">
                  {step.sub.split("\n").map((line, li) => (
                    <React.Fragment key={li}>{line}{li === 0 && <br />}</React.Fragment>
                  ))}
                </p>
              </motion.div>

              {/* Arrow between steps */}
              {i < STEPS.length - 1 && (
                <motion.div
                  initial={{ opacity: 0, scaleX: 0 }}
                  whileInView={{ opacity: 1, scaleX: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.13 + 0.25, duration: 0.35, ease: EASE }}
                  className="hidden origin-left items-center md:flex"
                  style={{ marginTop: 72, paddingInline: 8 }}
                >
                  <div className="flex items-center gap-0">
                    <div className="h-px w-10 bg-gradient-to-r from-white/15 to-white/35" />
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M1 7h10M8 3l4 4-4 4" stroke="rgba(255,255,255,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                </motion.div>
              )}

              {/* Mobile arrow (vertical) */}
              {i < STEPS.length - 1 && (
                <motion.div
                  initial={{ opacity: 0 }} whileInView={{ opacity: 1 }}
                  viewport={{ once: true }} transition={{ delay: i * 0.13 + 0.2 }}
                  className="flex items-center md:hidden"
                >
                  <svg width="14" height="24" viewBox="0 0 14 24" fill="none">
                    <path d="M7 1v16M3 14l4 4 4-4" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </motion.div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
