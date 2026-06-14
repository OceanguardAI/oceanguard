import React, { useState } from "react";
import { askOceanGuard } from "../lib/api";
import { MessageSquare, Send } from "lucide-react";

export default function AskOceanGuard() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState<{q: string; a: string}[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const currentQ = query;
    setQuery("");
    setLoading(true);
    
    try {
      const res = await askOceanGuard(currentQ);
      setHistory(prev => [...prev, { q: currentQ, a: res.answer }]);
    } catch (err) {
      setHistory(prev => [...prev, { q: currentQ, a: "Sorry, the agent encountered an error." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-ocean-800 border border-ocean-700 rounded-lg flex flex-col shadow-lg h-[300px]">
      <div className="p-3 border-b border-ocean-700 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-teal-400" />
        <h3 className="text-xs font-semibold text-teal-400 uppercase tracking-wider">Ask OceanGuard</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        {history.length === 0 && !loading && (
          <div className="text-slate-500 text-center mt-8">Ask a question about the detections, MPA distances, or risk scores.</div>
        )}
        {history.map((h, i) => (
          <div key={i} className="space-y-2">
            <div className="text-slate-300 font-medium">Q: {h.q}</div>
            <div className="text-slate-400 pl-4 border-l-2 border-ocean-600 bg-ocean-900/30 p-2 rounded-r">{h.a}</div>
          </div>
        ))}
        {loading && <div className="text-teal-400/70 animate-pulse text-xs font-medium">Agent is thinking...</div>}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-ocean-700 flex gap-2">
        <input 
          type="text" 
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 bg-ocean-900 border border-ocean-700 rounded px-3 py-1.5 text-sm text-slate-200 outline-none focus:border-teal-500 transition-colors"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading || !query.trim()}
          className="bg-teal-600 hover:bg-teal-500 disabled:bg-ocean-700 text-white rounded p-1.5 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
