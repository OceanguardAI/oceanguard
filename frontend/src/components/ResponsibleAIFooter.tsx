import React from "react";
import { AlertCircle } from "lucide-react";

export default function ResponsibleAIFooter() {
  return (
    <footer className="shrink-0 border-t border-ocean-700/20 bg-ocean-950/80 py-2 px-4">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-2 text-[11px] text-slate-600">
        <AlertCircle className="w-3 h-3 text-risk-medium shrink-0" />
        <span className="font-semibold text-slate-500">Responsible AI Notice:</span>
        <span>
          OceanGuard provides decision-support analysis only. AI outputs must be verified by a
          human conservation officer before any enforcement action is taken.
        </span>
      </div>
    </footer>
  );
}
