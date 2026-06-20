import React, { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";

interface TooltipProps {
  title: string;
  body: string;
  /** A highlighted call-out explaining why / when an officer uses this */
  highlight?: { label: string; text: string };
  /** Optional icon shown in the popup header (same icon as the chip itself) */
  icon?: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  /** Preferred horizontal anchor; clamped to the viewport so it never clips */
  align?: "left" | "center" | "right";
}

const W = 320;        // tooltip width (w-80)
const GAP = 8;        // gap between trigger and tooltip
const MARGIN = 8;     // min distance from any viewport edge

interface Pos {
  left: number;
  topBelow: number;
  bottomAbove: number;
  placement: "below" | "above";
  arrowLeft: number;
}

export default function Tooltip({
  title, body, highlight, icon: Icon, children, align = "center",
}: TooltipProps) {
  const triggerRef = useRef<HTMLDivElement>(null);
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState<Pos>({
    left: 0, topBelow: 0, bottomAbove: 0, placement: "below", arrowLeft: W / 2,
  });

  // Measure the trigger and place the popup against the viewport. Rendered in a
  // portal with `position: fixed`, so no scroll/overflow ancestor can clip it.
  const compute = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r  = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    let left =
      align === "left"  ? r.left :
      align === "right" ? r.right - W :
      r.left + r.width / 2 - W / 2;
    left = Math.max(MARGIN, Math.min(left, vw - W - MARGIN));

    // Flip above the trigger when there isn't room below it.
    const estH = highlight ? 240 : 150;
    const placement: "below" | "above" = r.bottom + GAP + estH <= vh ? "below" : "above";

    const arrowLeft = Math.max(16, Math.min(r.left + r.width / 2 - left, W - 16));

    setPos({
      left,
      topBelow: r.bottom + GAP,
      bottomAbove: vh - (r.top - GAP),
      placement,
      arrowLeft,
    });
  }, [align, highlight]);

  const open  = () => { compute(); setShow(true); };
  const close = () => setShow(false);

  // Keep the popup glued to the trigger if the page or an inner panel scrolls.
  useEffect(() => {
    if (!show) return;
    const onMove = () => compute();
    window.addEventListener("scroll", onMove, true);   // capture: catches inner scrollers
    window.addEventListener("resize", onMove);
    return () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }, [show, compute]);

  const below = pos.placement === "below";

  return (
    <div
      ref={triggerRef}
      className="relative"
      onMouseEnter={open}
      onMouseLeave={close}
    >
      {children}
      {createPortal(
        <AnimatePresence>
          {show && (
            <motion.div
              initial={{ opacity: 0, y: below ? -8 : 8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{    opacity: 0, y: below ? -8 : 8, scale: 0.95 }}
              transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
              style={{
                position: "fixed",
                left: pos.left,
                top:    below ? pos.topBelow : undefined,
                bottom: below ? undefined : pos.bottomAbove,
                width: W,
              }}
              className="z-[9999] pointer-events-none"
            >
              <div className="relative overflow-hidden rounded-2xl border border-white/12 bg-ocean-900/70 backdrop-blur-2xl shadow-[0_20px_60px_-12px_rgba(0,0,0,0.7)]">
                <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />
                <div className="pointer-events-none absolute -top-16 -right-10 h-32 w-32 rounded-full bg-cyan-400/10 blur-3xl" />

                <div className="relative p-4">
                  <div className="flex items-center gap-2 mb-2">
                    {Icon && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-cyan-300/20 bg-cyan-400/10">
                        <Icon className="h-3.5 w-3.5 text-cyan-300" />
                      </div>
                    )}
                    <div className="text-[13px] font-semibold text-white">{title}</div>
                  </div>

                  <div className="text-xs leading-relaxed text-slate-300">{body}</div>

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

              {/* arrow — at the top when below, at the bottom when flipped above */}
              <div
                style={{ left: pos.arrowLeft }}
                className={`absolute h-2.5 w-2.5 -translate-x-1/2 rotate-45 rounded-[2px] bg-ocean-900/70 backdrop-blur-2xl ${
                  below ? "-top-[5px] border-t border-l border-white/12"
                        : "-bottom-[5px] border-b border-r border-white/12"
                }`}
              />
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
