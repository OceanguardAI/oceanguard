import React, { useEffect, useState } from "react";
import { ModelMetrics } from "../types";
import { fetchModelMetrics } from "../lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Target, TrendingUp, AlertTriangle } from "lucide-react";

export default function ModelMetricsComponent() {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    fetchModelMetrics()
      .then((data) => {
        if (!cancelled) setMetrics(data);
      })
      .catch(() => {
        if (!cancelled) {
          setMetrics(null);
          setError("Couldn't load model metrics. Check the backend and try again.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="text-risk-high p-8">{error}</div>;
  if (!metrics) return <div className="text-slate-400 p-8">Loading metrics...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">ML Model Validation</h2>
        <p className="text-slate-400">YOLO11n performance on the HRSID dataset and xView3 validation scenes.</p>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-ocean-800 border border-ocean-700 p-4 rounded-lg">
          <div className="text-slate-400 text-sm mb-1">mAP50</div>
          <div className="text-2xl font-bold text-white">{(metrics.map50 * 100).toFixed(1)}%</div>
        </div>
        <div className="bg-ocean-800 border border-ocean-700 p-4 rounded-lg">
          <div className="text-slate-400 text-sm mb-1">Precision</div>
          <div className="text-2xl font-bold text-white">{(metrics.precision * 100).toFixed(1)}%</div>
        </div>
        <div className="bg-ocean-800 border border-ocean-700 p-4 rounded-lg">
          <div className="text-slate-400 text-sm mb-1">Recall</div>
          <div className="text-2xl font-bold text-white">{(metrics.recall * 100).toFixed(1)}%</div>
        </div>
        <div className="bg-ocean-800 border border-ocean-700 p-4 rounded-lg">
          <div className="text-slate-400 text-sm mb-1">Conf Threshold</div>
          <div className="text-2xl font-bold text-white">{metrics.confidence_threshold}</div>
        </div>
      </div>

      {/* Chart */}
      {metrics.training_history && metrics.training_history.length > 0 && (
        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-6">Training Progress (mAP50 vs Loss)</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics.training_history} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1A3A5C" />
                <XAxis dataKey="epoch" stroke="#94a3b8" />
                <YAxis yAxisId="left" stroke="#25A5A8" name="mAP50" />
                <YAxis yAxisId="right" orientation="right" stroke="#f43f5e" name="Loss" />
                <Tooltip contentStyle={{ backgroundColor: '#0F2A4A', borderColor: '#1A3A5C' }} />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="map50" stroke="#25A5A8" strokeWidth={2} name="mAP50" />
                <Line yAxisId="right" type="monotone" dataKey="loss" stroke="#f43f5e" strokeWidth={2} name="Loss" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Model Info */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-teal-400" /> Model Configuration
          </h3>
          <ul className="space-y-3 text-sm text-slate-300">
            <li className="flex justify-between border-b border-ocean-700 pb-2">
              <span className="text-slate-500">Architecture</span>
              <span className="font-medium text-white">{metrics.model}</span>
            </li>
            <li className="flex justify-between border-b border-ocean-700 pb-2">
              <span className="text-slate-500">Dataset</span>
              <span className="font-medium text-white">{metrics.dataset}</span>
            </li>
            <li className="flex justify-between border-b border-ocean-700 pb-2">
              <span className="text-slate-500">Epochs Trained</span>
              <span className="font-medium text-white">{metrics.epochs}</span>
            </li>
          </ul>
        </div>

        <div className="bg-ocean-800 border border-ocean-700 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-teal-400" /> Real-World Validation
          </h3>
          <p className="text-sm text-slate-300 mb-4 leading-relaxed">
            The model was run against the unlabelled <strong className="text-white">{metrics.validation_scene}</strong> SAR scene to test generalisation on raw satellite data.
          </p>
          <div className="bg-ocean-900 border border-ocean-700 rounded p-4 flex items-center gap-4">
            <div className="bg-teal-500/20 text-teal-400 w-12 h-12 rounded-full flex items-center justify-center font-bold text-xl shrink-0">
              {metrics.detections_on_real_scene}
            </div>
            <div className="text-sm">
              <div className="text-white font-medium">Vessels Detected</div>
              <div className="text-slate-400">on {metrics.validation_scene}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Limitations */}
      <div className="bg-risk-high/10 border border-risk-high/30 p-6 rounded-lg">
        <h3 className="text-lg font-semibold text-risk-high mb-2 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" /> Known Limitations
        </h3>
        <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
          <li>SAR imagery struggles with small wooden or fiberglass vessels (common in artisanal fishing).</li>
          <li>High wind speeds (&gt;10m/s) increase sea clutter, which may cause false positives.</li>
          <li>Confidence scores below 0.45 are filtered out to reduce noise.</li>
        </ul>
      </div>
    </div>
  );
}
