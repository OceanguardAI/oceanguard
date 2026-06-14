export function getRiskColor(level: string): string {
  switch (level.toUpperCase()) {
    case "CRITICAL": return "text-risk-critical";
    case "HIGH":     return "text-risk-high";
    case "MEDIUM":   return "text-risk-medium";
    case "LOW":      return "text-risk-low";
    default:         return "text-slate-400";
  }
}

export function getRiskBgColor(level: string): string {
  switch (level.toUpperCase()) {
    case "CRITICAL": return "bg-risk-critical/20 text-risk-critical border border-risk-critical/30";
    case "HIGH":     return "bg-risk-high/20 text-risk-high border border-risk-high/30";
    case "MEDIUM":   return "bg-risk-medium/20 text-risk-medium border border-risk-medium/30";
    case "LOW":      return "bg-risk-low/20 text-risk-low border border-risk-low/30";
    default:         return "bg-slate-800 text-slate-400";
  }
}
