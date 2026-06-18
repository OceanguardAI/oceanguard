import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ModelMetrics } from "../types";
import { fetchModelMetrics } from "../lib/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { Target, TrendingUp, AlertTriangle, Loader2 } from "lucide-react";

const METRIC_CARD = "rounded-xl border border-ocean-700/60 bg-ocean-800/50 p-5";

export default function ModelMetricsComponent() {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchModelMetrics()
      .then((data) => { if (!cancelled) setMetrics(data); })
      .catch(() => { if (!cancelled) setError("Couldn't load model metrics. Check the backend."); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-risk-high/20 bg-risk-high/5 p-6 text-sm text-risk-high">
        <AlertTriangle className="w-5 h-5 shrink-0" /> {error}
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex items-center gap-3 text-slate-400 py-12">
        <Loader2 className="w-5 h-5 animate-spin text-teal-400" />
        Loading ML metrics…
      </div>
    );
  }

  const stats = [
    { label: "mAP50",           value: `${(metrics.map50 * 100).toFixed(1)}%`,       sub: "Primary metric"      },
    { label: "mAP50-95",        value: `${(metrics.map50_95 * 100).toFixed(1)}%`,    sub: "Strict IoU metric"   },
    { label: "Precision",       value: `${(metrics.precision * 100).toFixed(1)}%`,   sub: "TP / (TP + FP)"     },
    { label: "Recall",          value: `${(metrics.recall * 100).toFixed(1)}%`,      sub: "TP / (TP + FN)"     },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-extrabold text-white mb-1">ML Model Validation</h2>
        <p className="text-slate-400 text-sm">YOLO11n performance on the HRSID dataset and xView3 validation scenes.</p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.07 }}
            className={METRIC_CARD}
          >
            <div className="text-xs text-slate-500 mb-1 font-medium">{s.label}</div>
            <div className="text-2xl font-extrabold text-white mb-0.5">{s.value}</div>
            <div className="text-[11px] text-slate-600">{s.sub}</div>
          </motion.div>
        ))}
      </div>

      {/* Training chart */}
      {metrics.training_history && metrics.training_history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className={`${METRIC_CARD} !p-6`}
        >
          <h3 className="text-base font-bold text-white mb-5">Training Progress · mAP50 vs Loss</h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics.training_history} margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" />
                <XAxis dataKey="epoch" stroke="#475569" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="left"  stroke="#25A5A8" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" stroke="#f43f5e" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0B1F3A", borderColor: "#1A3A5C", borderRadius: 10, fontSize: 12 }}
                  labelStyle={{ color: "#94a3b8" }}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
                <Line yAxisId="left"  type="monotone" dataKey="map50" stroke="#25A5A8" strokeWidth={2} dot={false} name="mAP50" />
                <Line yAxisId="right" type="monotone" dataKey="loss"  stroke="#f43f5e" strokeWidth={2} dot={false} name="Loss"  />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      )}

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
          className={METRIC_CARD}
        >
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-teal-400" /> Model Configuration
          </h3>
          <ul className="space-y-2.5">
            {[
              { label: "Architecture", value: metrics.model   },
              { label: "Dataset",      value: metrics.dataset  },
              { label: "Epochs",       value: metrics.epochs   },
              { label: "Conf Threshold", value: metrics.confidence_threshold },
            ].map((row) => (
              <li key={row.label} className="flex justify-between items-center border-b border-ocean-700/30 pb-2 last:border-0 last:pb-0">
                <span className="text-xs text-slate-500">{row.label}</span>
                <span className="text-xs font-semibold text-white">{row.value}</span>
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.48 }}
          className={METRIC_CARD}
        >
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-teal-400" /> Real-World Validation
          </h3>
          <p className="text-xs text-slate-400 mb-4 leading-relaxed">
            Tested on unlabelled <strong className="text-white">{metrics.validation_scene}</strong> SAR scene to measure generalisation on raw satellite data.
          </p>
          <div className="flex items-center gap-4 bg-ocean-900/50 rounded-xl p-4 border border-ocean-700/30">
            <div className="w-12 h-12 rounded-full bg-teal-400/10 border border-teal-400/20 flex items-center justify-center font-extrabold text-xl text-teal-400 shrink-0">
              {metrics.detections_on_real_scene}
            </div>
            <div>
              <div className="text-sm font-bold text-white">Vessels Detected</div>
              <div className="text-xs text-slate-500">{metrics.validation_scene}</div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Limitations */}
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.55 }}
        className="rounded-xl border border-risk-high/20 bg-risk-high/5 p-6"
      >
        <h3 className="text-sm font-bold text-risk-high mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> Known Limitations
        </h3>
        <ul className="list-disc list-inside text-xs text-slate-400 space-y-1.5 leading-relaxed">
          <li>SAR struggles with small wooden or fiberglass vessels common in artisanal fishing.</li>
          <li>High wind speeds (&gt;10 m/s) increase sea clutter and may cause false positives.</li>
          <li>Confidence scores below {metrics.confidence_threshold} are filtered to reduce noise.</li>
        </ul>
      </motion.div>
    </div>
  );
}
