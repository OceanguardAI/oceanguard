import React from "react";
import { Menu, Satellite, Waves, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import GradientButton from "../ui/GradientButton";

type NavItem = {
  label: string;
  target: string;
};

interface LandingNavbarProps {
  items: NavItem[];
  onOpenDashboard: () => void;
  onJump: (target: string) => void;
}

export default function LandingNavbar({
  items,
  onOpenDashboard,
  onJump,
}: LandingNavbarProps) {
  const [open, setOpen] = React.useState(false);

  const handleJump = (target: string) => {
    setOpen(false);
    onJump(target);
  };

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4 md:px-6">
      <div className="mx-auto flex max-w-7xl items-center justify-between rounded-full border border-cyan-400/10 bg-ocean-950/70 px-4 py-3 shadow-[0_20px_80px_rgba(2,8,23,0.45)] backdrop-blur-xl md:px-6">
        <button
          onClick={() => handleJump("hero")}
          className="flex items-center gap-3 text-left"
          aria-label="OceanGuard AI home"
        >
          <div className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-cyan-300/10 via-ocean-800 to-teal-500/10">
            <img src="/branding/oceanguard-mark.png" alt="OceanGuard AI mark" className="h-8 w-8 rounded-xl object-cover" />
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,211,238,0.3),transparent_45%)]" />
          </div>
          <div>
            <div className="font-display text-lg font-semibold tracking-tight text-white">
              OceanGuard <span className="text-cyan-300">AI</span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.22em] text-slate-500">
              <Satellite className="h-3 w-3" />
              Deep Ocean Intelligence
            </div>
          </div>
        </button>

        <nav className="hidden items-center gap-6 md:flex">
          {items.map((item) => (
            <button
              key={item.target}
              onClick={() => handleJump(item.target)}
              className="text-sm text-slate-400 transition-colors hover:text-cyan-200"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <div className="rounded-full border border-teal-400/15 bg-teal-400/5 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-teal-200/80">
            SDG 14
          </div>
          <GradientButton variant="primary" size="sm" onClick={onOpenDashboard}>
            Open Dashboard
          </GradientButton>
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          className="flex h-11 w-11 items-center justify-center rounded-full border border-cyan-400/10 bg-ocean-900/70 text-slate-200 md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
            className="mx-auto mt-3 max-w-7xl rounded-3xl border border-cyan-400/10 bg-ocean-950/95 p-4 shadow-2xl backdrop-blur-xl md:hidden"
          >
            <div className="mb-4 flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500">
              <Waves className="h-3 w-3" />
              Navigation
            </div>
            <div className="space-y-2">
              {items.map((item) => (
                <button
                  key={item.target}
                  onClick={() => handleJump(item.target)}
                  className="flex w-full rounded-2xl border border-ocean-700/60 bg-ocean-900/70 px-4 py-3 text-left text-sm text-slate-300 transition-colors hover:border-cyan-400/20 hover:text-white"
                >
                  {item.label}
                </button>
              ))}
              <GradientButton
                variant="primary"
                size="md"
                onClick={() => {
                  setOpen(false);
                  onOpenDashboard();
                }}
                className="mt-2 w-full justify-center"
              >
                Open Dashboard
              </GradientButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
