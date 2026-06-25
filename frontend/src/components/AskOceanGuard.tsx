import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { askOceanGuard } from "../lib/api";
import { Send, Bot, User, Loader2 } from "lucide-react";

function cleanAnswer(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")   // **bold**
    .replace(/__(.*?)__/g, "$1")        // __bold__
    .replace(/^\s*#{1,6}\s*/gm, "")    // # headings
    .replace(/^\s*\*\s+/gm, "- ")      // * bullets → - bullets
    .replace(/[*_`]+/g, "")            // stray emphasis chars
    .replace(/\n{3,}/g, "\n\n")        // collapse excess blank lines
    .trim();
}

interface Message { role: "user" | "ai"; text: string; }

const SUGGESTIONS = [
  "What is the highest-risk detection?",
  "Which vessels are inside the MPA?",
  "How is risk score calculated?",
];

export default function AskOceanGuard() {
  const [query, setQuery]     = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef             = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || loading) return;
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await askOceanGuard(q);
      setMessages((prev) => [...prev, { role: "ai", text: res.answer }]);
    } catch {
      setMessages((prev) => [...prev, { role: "ai", text: "The agent encountered an error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); send(query); };

  return (
    <div className="rounded-xl border border-ocean-700/60 bg-ocean-800/50 backdrop-blur-sm overflow-hidden shadow-lg flex flex-col h-full min-h-[320px]">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-ocean-700/40 shrink-0">
        <div className="w-5 h-5 rounded-md bg-gradient-to-br from-teal-500 to-teal-400 flex items-center justify-center">
          <Bot className="w-3 h-3 text-white" />
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-teal-400">Ask OceanGuard</span>
        <span className="ml-auto text-[10px] text-slate-600">AI Analyst</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.length === 0 && !loading && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="space-y-2 pt-1"
          >
            <p className="text-[11px] text-slate-500 text-center">Ask about detections, risk scores, or MPA data.</p>
            <div className="flex flex-col gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-left text-[11px] px-3 py-1.5 rounded-lg bg-ocean-700/30 border border-ocean-700/40 text-slate-400 hover:text-teal-400 hover:border-teal-400/20 transition-all duration-150"
                >
                  {s}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
              className={`flex gap-2 ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                m.role === "user" ? "bg-ocean-600" : "bg-teal-500/20 border border-teal-400/20"
              }`}>
                {m.role === "user"
                  ? <User className="w-2.5 h-2.5 text-slate-300" />
                  : <Bot className="w-2.5 h-2.5 text-teal-400" />}
              </div>
              <div className={`max-w-[82%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                m.role === "user"
                  ? "bg-ocean-700/60 text-slate-200 rounded-tr-none"
                  : "bg-teal-400/6 border border-teal-400/10 text-slate-300 rounded-tl-none"
              }`}>
                {m.role === "ai"
                  ? cleanAnswer(m.text).split("\n").map((line, li, arr) => (
                      <React.Fragment key={li}>
                        {line}
                        {li < arr.length - 1 && <br />}
                      </React.Fragment>
                    ))
                  : m.text}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="flex gap-2"
          >
            <div className="w-5 h-5 rounded-full bg-teal-500/20 border border-teal-400/20 flex items-center justify-center shrink-0">
              <Bot className="w-2.5 h-2.5 text-teal-400" />
            </div>
            <div className="px-3 py-2 bg-teal-400/6 border border-teal-400/10 rounded-xl rounded-tl-none">
              <Loader2 className="w-3 h-3 animate-spin text-teal-400" />
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="shrink-0 flex gap-2 p-3 border-t border-ocean-700/40 bg-ocean-900/30">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question…"
          disabled={loading}
          className="flex-1 bg-ocean-900/60 border border-ocean-700/50 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-teal-400/40 transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="w-7 h-7 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:bg-ocean-700 text-white flex items-center justify-center transition-colors shrink-0"
        >
          <Send className="w-3 h-3" />
        </button>
      </form>
    </div>
  );
}
