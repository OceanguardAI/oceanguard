import React from "react";
import { clsx } from "clsx";

interface RiskBadgeProps {
  level: string;
  score?: number;
  size?: "xs" | "sm" | "md";
}

const COLORS: Record<string, string> = {
  LOW:      "bg-risk-low/10 text-risk-low border-risk-low/25",
  MEDIUM:   "bg-risk-medium/10 text-risk-medium border-risk-medium/25",
  HIGH:     "bg-risk-high/10 text-risk-high border-risk-high/25",
  CRITICAL: "bg-risk-critical/10 text-risk-critical border-risk-critical/25",
};

const DOTS: Record<string, string> = {
  LOW:      "bg-risk-low",
  MEDIUM:   "bg-risk-medium",
  HIGH:     "bg-risk-high",
  CRITICAL: "bg-risk-critical animate-pulse",
};

const SIZES = {
  xs: "px-1.5 py-0.5 text-[10px] gap-1",
  sm: "px-2.5 py-1 text-xs gap-1.5",
  md: "px-3 py-1.5 text-sm gap-2",
};

export default function RiskBadge({ level, score, size = "sm" }: RiskBadgeProps) {
  const upper = level?.toUpperCase() ?? "LOW";
  return (
    <span
      className={clsx(
        "inline-flex items-center font-bold uppercase tracking-wider rounded-full border",
        COLORS[upper] ?? "bg-slate-800/50 text-slate-400 border-slate-700",
        SIZES[size]
      )}
    >
      <span className={clsx("rounded-full shrink-0", upper === "xs" ? "w-1 h-1" : "w-1.5 h-1.5", DOTS[upper] ?? "bg-slate-400")} />
      {upper}
      {score !== undefined && (
        <span className="opacity-70 font-normal ml-0.5">· {(score * 100).toFixed(0)}</span>
      )}
    </span>
  );
}
