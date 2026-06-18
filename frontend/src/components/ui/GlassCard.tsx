import React from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: boolean;
  hover?: boolean;
  onClick?: () => void;
}

export default function GlassCard({ children, className, glow = false, hover = false, onClick }: GlassCardProps) {
  return (
    <motion.div
      onClick={onClick}
      whileHover={hover ? { y: -2 } : undefined}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className={clsx(
        "rounded-xl border transition-colors duration-200",
        "bg-ocean-800/50 backdrop-blur-md",
        glow
          ? "border-teal-400/20 shadow-lg shadow-teal-400/5"
          : "border-ocean-700/60",
        hover && "cursor-pointer hover:border-teal-400/20",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
