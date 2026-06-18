import React from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";

interface GradientButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "xs" | "sm" | "md" | "lg";
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  className?: string;
}

export default function GradientButton({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled = false,
  type = "button",
  className,
}: GradientButtonProps) {
  const sizes: Record<string, string> = {
    xs: "px-2.5 py-1 text-xs gap-1",
    sm: "px-4 py-1.5 text-xs gap-1.5",
    md: "px-5 py-2 text-sm gap-2",
    lg: "px-7 py-3 text-base gap-2",
  };

  const variants: Record<string, string> = {
    primary:
      "bg-gradient-to-r from-teal-600 to-teal-400 text-white hover:from-teal-500 hover:to-teal-300 shadow-lg shadow-teal-500/20",
    secondary:
      "bg-ocean-800 border border-teal-400/25 text-teal-400 hover:bg-ocean-700 hover:border-teal-400/50",
    ghost:
      "text-slate-300 hover:text-white hover:bg-ocean-800/60",
    danger:
      "bg-risk-critical/15 border border-risk-critical/30 text-risk-critical hover:bg-risk-critical/25",
  };

  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={{ duration: 0.13 }}
      className={clsx(
        "inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200 select-none",
        sizes[size],
        variants[variant],
        disabled && "opacity-40 cursor-not-allowed pointer-events-none",
        className
      )}
    >
      {children}
    </motion.button>
  );
}
