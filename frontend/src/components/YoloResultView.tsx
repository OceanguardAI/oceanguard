import React from "react";
import { Radar, ShieldCheck, SearchX } from "lucide-react";
import { YoloVerifyResult } from "../lib/api";

/** Renders a YOLO verification result: the found/not-found verdict plus the
 *  exact Sentinel-1 chip the model analysed, with its detection boxes drawn on
 *  top. Shared by the Evidence card (verifying a known detection) and the
 *  area-scan panel (verifying an arbitrary point the officer clicked). */
export default function YoloResultView({
  result,
  label,
}: {
  result: YoloVerifyResult;
  label: string;
}) {
  const y = result.yolo;
  return (
    <div className="space-y-3">
      {y.found ? (
        <div className="flex items-center gap-2 flex-wrap text-xs font-semibold text-risk-low">
          <ShieldCheck className="w-4 h-4 shrink-0" />
          Vessel confirmed · {(y.best_confidence * 100).toFixed(0)}% ·{" "}
          {y.count} contact{y.count > 1 ? "s" : ""}
          {result.agreement && (
            <span className="text-cyan-300">· confirmed by 2 independent systems</span>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <SearchX className="w-4 h-4 shrink-0" />
          No vessel found in this radar pass.
        </div>
      )}

      <div className="relative rounded-lg overflow-hidden border border-ocean-700/40">
        <img
          src={`data:image/png;base64,${y.chip_png_b64}`}
          alt={`YOLO-analysed Sentinel-1 chip for ${label}`}
          className="w-full block"
        />
        <svg
          viewBox={`0 0 ${y.chip_px} ${y.chip_px}`}
          preserveAspectRatio="none"
          className="absolute inset-0 w-full h-full pointer-events-none"
        >
          {y.detections.map((d, i) => (
            <g key={i}>
              <rect
                x={d.bbox_px[0]} y={d.bbox_px[1]}
                width={d.bbox_px[2] - d.bbox_px[0]}
                height={d.bbox_px[3] - d.bbox_px[1]}
                fill="none" stroke="#22d3ee" strokeWidth={3}
              />
              <text
                x={d.bbox_px[0]} y={Math.max(13, d.bbox_px[1] - 4)}
                fill="#22d3ee" fontSize={14} fontWeight="bold"
              >
                {(d.confidence * 100).toFixed(0)}%
              </text>
            </g>
          ))}
        </svg>
        <div className="absolute bottom-0 left-0 right-0 flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-t from-ocean-900/90 to-transparent text-[10px] text-slate-300">
          <Radar className="w-3 h-3 text-cyan-400" />
          OceanGuard YOLO · Sentinel-1 VV · conf ≥ {(y.conf_threshold * 100).toFixed(0)}%
        </div>
      </div>
    </div>
  );
}
