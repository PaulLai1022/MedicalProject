import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface OriginDotProps {
  origin: "machine" | "user";
  machineValue?: string | string[] | null;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function OriginDot({
  origin,
  machineValue,
  showLabel = false,
  size = "md",
}: OriginDotProps) {
  const [open, setOpen] = useState(false);
  const isUser = origin === "user";

  const ringSize = size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5";
  const dotSize  = size === "sm" ? "h-1.5 w-1.5" : "h-1.5 w-1.5";

  const display = Array.isArray(machineValue)
    ? machineValue.length > 0 ? machineValue.join(", ") : "(empty)"
    : (machineValue ?? "(empty)");

  return (
    <span
      className="relative inline-flex items-center gap-1.5"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span
        className={[
          "grid place-items-center rounded-full transition-colors",
          ringSize,
          isUser ? "bg-edited-100" : "bg-ink-100",
        ].join(" ")}
        aria-label={isUser ? "Edited by user" : "AI generated"}
      >
        <span
          className={[
            "rounded-full",
            dotSize,
            isUser ? "bg-edited-600" : "bg-ink-400",
          ].join(" ")}
        />
      </span>
      {showLabel && (
        <span
          className={[
            "text-[11px] font-medium",
            isUser ? "text-edited-700" : "text-ink-500",
          ].join(" ")}
        >
          {isUser ? "Edited" : "AI"}
        </span>
      )}

      <AnimatePresence>
        {open && isUser && machineValue != null && (
          <motion.span
            initial={{ opacity: 0, y: 4, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.96 }}
            transition={{ duration: 0.15, ease: [0.32, 0.72, 0, 1] }}
            className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-xl2 border border-ink-200 bg-white p-3 text-left shadow-lift"
          >
            <p className="mb-1 text-[10.5px] font-semibold uppercase tracking-wider text-ink-400">
              AI original
            </p>
            <p className="max-h-32 overflow-y-auto whitespace-pre-wrap break-words text-[12px] leading-relaxed text-ink-700">
              {display}
            </p>
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
