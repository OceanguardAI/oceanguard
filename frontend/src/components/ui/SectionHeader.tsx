import React from "react";
import { clsx } from "clsx";

interface SectionHeaderProps {
  icon?: React.ReactNode;
  label: string;
  title?: string;
  subtitle?: string;
  className?: string;
  accent?: boolean;
}

export default function SectionHeader({
  icon,
  label,
  title,
  subtitle,
  className,
  accent = true,
}: SectionHeaderProps) {
  return (
    <div className={clsx("space-y-0.5", className)}>
      <div className="flex items-center gap-1.5">
        {icon && <span className="text-teal-400 flex items-center">{icon}</span>}
        <span
          className={clsx(
            "text-[10px] font-semibold uppercase tracking-[0.12em]",
            accent ? "text-teal-400" : "text-slate-500"
          )}
        >
          {label}
        </span>
      </div>
      {title && (
        <h2 className="text-lg font-bold text-white leading-tight">{title}</h2>
      )}
      {subtitle && (
        <p className="text-xs text-slate-400 leading-relaxed">{subtitle}</p>
      )}
    </div>
  );
}
