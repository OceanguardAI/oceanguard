import React, { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  className?: string;
}

export default function AnimatedNumber({
  value,
  duration = 900,
  suffix = "",
  prefix = "",
  decimals = 0,
  className,
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(0);
  const prevRef    = useRef(0);
  const startRef   = useRef<number | null>(null);
  const rafRef     = useRef<number | null>(null);
  const targetRef  = useRef(value);

  useEffect(() => {
    targetRef.current = value;
    const from = prevRef.current;
    startRef.current = null;

    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);

    const tick = (ts: number) => {
      if (startRef.current === null) startRef.current = ts;
      const elapsed  = ts - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3);
      const current  = from + (targetRef.current - from) * eased;
      setDisplay(current);
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        prevRef.current = targetRef.current;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <span className={clsx("tabular-nums", className)}>
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
