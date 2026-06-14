import React from "react";
import { AlertCircle } from "lucide-react";

export default function ResponsibleAIFooter() {
  return (
    <footer className="bg-ocean-950 border-t border-ocean-800 p-2 shrink-0">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-2 text-xs text-slate-500">
        <AlertCircle className="w-3 h-3 text-risk-medium" />
        <span className="font-medium text-slate-400">Responsible AI Notice:</span>
        <span>
          OceanGuard provides decision-support analysis. AI outputs must be verified by a human conservation officer before any enforcement action is taken.
        </span>
      </div>
    </footer>
  );
}
