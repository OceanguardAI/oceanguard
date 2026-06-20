import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface TooltipProps {
  title: string;
  body: string;
  /** A highlighted call-out explaining why / when an officer uses this */
  highlight?: { label: string; text: string };
  /** Optional icon shown in the popup header (same icon as the chip itself) */
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  /** Which edge to anchor the popup against — avoids off-screen overflow */
  align?: "left" | "center" | "right";
}

export default function Tooltip({
  title, body, highlight, icon: Icon, children, align = "center",
}: TooltipProps) {
  const [show, setShow] = useState(false);

  const alignClass =
    align === "left"  ? "left-0" :
    align === "right" ? "right-0" :
    "left-1/2 -translate-x-1/2";

  const arrowClass =
    align === "right" ? "right-5" :
    align === "left"  ? "left-5" :
    "left-1/2 -translate-x-1/2";

  return (
    <div
      className="relative"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0,  scale: 1    }}
            exit={{    opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
            className={`absolute top-full mt-3 z-50 w-80 pointer-events-none ${alignClass}`}
          >
            {/* glass card */}
            <div className="relative overflow-hidden rounded-2xl border border-white/12 bg-ocean-900/70 backdrop-blur-2xl shadow-[0_20px_60px_-12px_rgba(0,0,0,0.7)]">
              {/* subtle top sheen for the glass effect */}
              <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />
              <div className="pointer-events-none absolute -top-16 -right-10 h-32 w-32 rounded-full bg-cyan-400/10 blur-3xl" />

              <div className="relative p-4">
                {/* header */}
                <div className="flex items-center gap-2 mb-2">
                  {Icon && (
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-cyan-300/20 bg-cyan-400/10">
                      <Icon className="h-3.5 w-3.5 text-cyan-300" />
                    </div>
                  )}
                  <div className="text-[13px] font-semibold text-white">{title}</div>
                </div>

                {/* what it is */}
                <div className="text-xs leading-relaxed text-slate-300">{body}</div>

                {/* why / when to use it */}
                {highlight && (
                  <div className="mt-3 rounded-xl border border-cyan-300/15 bg-cyan-400/[0.06] p-2.5">
                    <div className="text-[9px] font-semibold uppercase tracking-[0.18em] text-cyan-300 mb-1">
                      {highlight.label}
                    </div>
                    <div className="text-[11px] leading-relaxed text-slate-300">{highlight.text}</div>
                  </div>
                )}
              </div>
            </div>

            {/* arrow */}
            <div
              className={`absolute -top-[5px] h-2.5 w-2.5 rotate-45 rounded-[2px] border-t border-l border-white/12 bg-ocean-900/70 backdrop-blur-2xl ${arrowClass}`}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
