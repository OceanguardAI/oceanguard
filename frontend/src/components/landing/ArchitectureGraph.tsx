import React from "react";
import {
  ActivitySquare,
  Bot,
  FileText,
  MapPinned,
  Radar,
  ScanSearch,
  ShieldCheck,
  ShipWheel,
  Sparkles,
  Waves,
} from "lucide-react";
import { motion } from "framer-motion";

type Node = {
  id: string;
  label: string;
  desc: string;
  x: number;
  y: number;
  icon: React.ComponentType<{ className?: string }>;
};

const NODES: Node[] = [
  { id: "sar", label: "Sentinel-1 SAR", desc: "Raw ocean radar imagery", x: 7, y: 18, icon: Radar },
  { id: "prep", label: "SAR preprocessing", desc: "Tiles, cleanup, normalization", x: 27, y: 14, icon: Waves },
  { id: "yolo", label: "YOLO vessel detector", desc: "Vessel-like target detection", x: 48, y: 18, icon: ScanSearch },
  { id: "coords", label: "Detection coordinates", desc: "Structured lat/lon events", x: 68, y: 14, icon: ActivitySquare },
  { id: "ais", label: "AIS evidence comparison", desc: "GFW and AIS corroboration", x: 88, y: 18, icon: ShipWheel },
  { id: "mpa", label: "Protected-area check", desc: "WDPA / MPA proximity", x: 23, y: 67, icon: MapPinned },
  { id: "risk", label: "Risk scoring engine", desc: "Transparent prioritization", x: 43, y: 83, icon: ShieldCheck },
  { id: "ai", label: "AI evidence writer", desc: "Explainable evidence narrative", x: 63, y: 67, icon: Sparkles },
  { id: "card", label: "Evidence card", desc: "Review-ready case file", x: 81, y: 83, icon: FileText },
  { id: "human", label: "Human analyst review", desc: "Decision support only", x: 94, y: 60, icon: Bot },
];

const EDGES: Array<[string, string]> = [
  ["sar", "prep"],
  ["prep", "yolo"],
  ["yolo", "coords"],
  ["coords", "ais"],
  ["coords", "mpa"],
  ["ais", "risk"],
  ["mpa", "risk"],
  ["risk", "ai"],
  ["ai", "card"],
  ["card", "human"],
];

function centerOf(id: string) {
  const node = NODES.find((n) => n.id === id)!;
  return { x: node.x, y: node.y };
}

export default function ArchitectureGraph() {
  return (
    <div className="rounded-[2rem] border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(6,24,38,0.92),rgba(2,8,23,0.98))] p-5 shadow-[0_24px_100px_rgba(2,8,23,0.45)] md:p-8">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-[0.24em] text-cyan-300">How It Works</div>
          <div className="font-display text-2xl text-white md:text-3xl">From signal to evidence card</div>
        </div>
        <div className="hidden rounded-full border border-cyan-300/10 bg-cyan-300/5 px-3 py-1 text-[11px] text-slate-400 md:block">
          Human review stays in the loop
        </div>
      </div>

      <div className="hidden md:block">
        <div className="relative aspect-[16/9] overflow-hidden rounded-[1.5rem] border border-cyan-300/10 bg-ocean-950/70">
          <div className="absolute inset-0 ocean-grid opacity-40" />
          <div className="absolute inset-0 ocean-contours opacity-30" />
          <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full">
            <defs>
              <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(34,211,238,0.55)" />
                <stop offset="100%" stopColor="rgba(20,184,166,0.18)" />
              </linearGradient>
            </defs>
            {EDGES.map(([a, b], i) => {
              const from = centerOf(a);
              const to = centerOf(b);
              const midX = (from.x + to.x) / 2;
              const midY = Math.min(from.y, to.y) - 10;
              return (
                <motion.path
                  key={`${a}-${b}`}
                  d={`M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`}
                  fill="none"
                  stroke="url(#edgeGradient)"
                  strokeWidth="0.7"
                  strokeDasharray="0.6 1.2"
                  initial={{ pathLength: 0, opacity: 0.2 }}
                  whileInView={{ pathLength: 1, opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8, delay: i * 0.05 }}
                />
              );
            })}
          </svg>

          {NODES.map((node, i) => {
            const Icon = node.icon;
            return (
              <motion.div
                key={node.id}
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                whileInView={{ opacity: 1, y: 0, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.06 }}
                className="absolute w-[15rem] -translate-x-1/2 -translate-y-1/2 rounded-[1.4rem] border border-cyan-300/12 bg-ocean-900/80 p-4 shadow-[0_10px_40px_rgba(2,8,23,0.35)] backdrop-blur-xl"
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
              >
                <div className="mb-3 flex items-start gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-300/15 bg-cyan-300/8">
                    <Icon className="h-4 w-4 text-cyan-300" />
                  </div>
                  <div>
                    <div className="font-display text-sm text-white">{node.label}</div>
                    <div className="mt-1 text-[11px] leading-relaxed text-slate-400">{node.desc}</div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="grid gap-3 md:hidden">
        {NODES.map((node) => {
          const Icon = node.icon;
          return (
            <div
              key={node.id}
              className="rounded-[1.25rem] border border-cyan-300/10 bg-ocean-900/70 p-4"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-300/15 bg-cyan-300/8">
                  <Icon className="h-4 w-4 text-cyan-300" />
                </div>
                <div>
                  <div className="font-display text-sm text-white">{node.label}</div>
                  <div className="mt-1 text-xs leading-relaxed text-slate-400">{node.desc}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-5 text-sm leading-relaxed text-slate-400">
        OceanGuard does not make enforcement decisions. It supports human review with transparent evidence.
      </p>
    </div>
  );
}
