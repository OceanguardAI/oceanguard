import React from "react";
import { motion } from "framer-motion";
import { AlertTriangle, FileText, MapPinned, RadioTower, ScanSearch } from "lucide-react";

const FLOATING = [
  { label: "SAR Detection", icon: ScanSearch, className: "left-[-1rem] top-[12%] md:left-[-2rem]" },
  { label: "AIS Evidence", icon: RadioTower, className: "right-[-0.5rem] top-[20%] md:right-[-2rem]" },
  { label: "MPA Proximity", icon: MapPinned, className: "left-[4%] bottom-[12%]" },
  { label: "Evidence Card", icon: FileText, className: "right-[4%] bottom-[10%]" },
];

export default function DashboardPreview() {
  const [loaded, setLoaded] = React.useState(true);

  return (
    <div className="relative mx-auto w-full max-w-6xl">
      <div className="absolute inset-x-[12%] top-8 h-24 rounded-full bg-cyan-400/25 blur-[80px]" />
      <div className="absolute inset-x-[18%] top-24 h-40 rounded-full bg-teal-500/20 blur-[120px]" />

      <motion.div
        initial={{ opacity: 0, y: 24, rotateX: 8 }}
        whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
        className="relative rounded-[2rem] border border-cyan-300/10 bg-[linear-gradient(180deg,rgba(7,24,38,0.92),rgba(2,8,23,0.97))] p-3 shadow-[0_40px_140px_rgba(8,47,58,0.35)] md:p-5"
        style={{ transformStyle: "preserve-3d" }}
      >
        <div className="rounded-[1.6rem] border border-white/5 bg-ocean-950/90 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] md:p-4">
          <div className="mb-3 flex items-center justify-between rounded-[1.25rem] border border-cyan-300/10 bg-ocean-900/70 px-4 py-3 text-xs text-slate-400 md:px-5">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.8)]" />
              Live satellite detections transformed into review-ready cases.
            </div>
            <div className="hidden rounded-full border border-teal-400/15 bg-teal-400/5 px-3 py-1 text-[10px] uppercase tracking-[0.18em] text-teal-200/80 md:block">
              OceanGuard Monitoring
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[1.5rem] border border-cyan-300/10 bg-ocean-950">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,0.12),transparent_40%),linear-gradient(180deg,transparent,rgba(2,8,23,0.2))]" />
            {loaded ? (
              <img
                src="/landing/oceanguard-dashboard-preview.png"
                alt="OceanGuard dashboard preview"
                className="block w-full object-cover"
                onError={() => setLoaded(false)}
              />
            ) : (
              <div className="flex aspect-[16/9] items-center justify-center bg-[radial-gradient(circle_at_center,rgba(20,184,166,0.12),transparent_55%),linear-gradient(135deg,#061826,#020817)] p-10 text-center">
                <div className="max-w-md">
                  <AlertTriangle className="mx-auto mb-4 h-10 w-10 text-cyan-300" />
                  <div className="font-display text-2xl text-white">Dashboard preview ready</div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-400">
                    Drop the final screenshot into <code className="rounded bg-ocean-900 px-1.5 py-0.5 text-cyan-200">frontend/public/landing/oceanguard-dashboard-preview.png</code> and it will appear here automatically.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {FLOATING.map(({ label, icon: Icon, className }, i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, scale: 0.92 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 + i * 0.08, duration: 0.35 }}
            className={`absolute hidden rounded-full border border-cyan-300/15 bg-ocean-950/80 px-4 py-2 text-xs text-slate-200 shadow-[0_12px_40px_rgba(2,8,23,0.45)] backdrop-blur-xl md:flex ${className}`}
          >
            <div className="flex items-center gap-2">
              <Icon className="h-3.5 w-3.5 text-cyan-300" />
              {label}
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
