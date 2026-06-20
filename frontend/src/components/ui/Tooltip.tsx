import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface TooltipProps {
  title: string;
  body: string;
  children: React.ReactNode;
  /** Which edge to anchor the popup against — avoids off-screen overflow */
  align?: "left" | "center" | "right";
}

export default function Tooltip({ title, body, children, align = "center" }: TooltipProps) {
  const [show, setShow] = useState(false);

  const alignClass =
    align === "left"   ? "left-0" :
    align === "right"  ? "right-0" :
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
            initial={{ opacity: 0, y: -6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0,  scale: 1    }}
            exit={{    opacity: 0, y: -6, scale: 0.96 }}
            transition={{ duration: 0.14, ease: [0.22, 1, 0.36, 1] }}
            className={`absolute top-full mt-2.5 z-50 w-56 rounded-2xl border border-ocean-600/60
              bg-ocean-900/97 backdrop-blur-md shadow-2xl shadow-black/40 p-3.5 pointer-events-none ${alignClass}`}
          >
            {/* tiny arrow */}
            <div
              className={`absolute -top-[5px] w-2.5 h-2.5 rotate-45 rounded-[2px]
                border-t border-l border-ocean-600/60 bg-ocean-900/97
                ${align === "right" ? "right-4" : align === "left" ? "left-4" : "left-1/2 -translate-x-1/2"}`}
            />
            <div className="text-[11px] font-semibold text-white mb-1">{title}</div>
            <div className="text-[11px] text-slate-400 leading-relaxed">{body}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
