import { X } from "lucide-react";
import type { ReactNode } from "react";

export type ChipTone = "neutral" | "brand" | "warn" | "danger" | "edited";

const TONE: Record<ChipTone, string> = {
  neutral: "bg-ink-50      text-ink-700     ring-ink-200",
  brand:   "bg-brand-50    text-brand-700   ring-brand-100",
  warn:    "bg-observe-50  text-observe-700 ring-observe-100",
  danger:  "bg-admit-50    text-admit-700   ring-admit-100",
  edited:  "bg-edited-50   text-edited-700  ring-edited-100",
};

interface ChipProps {
  children: ReactNode;
  onRemove?: () => void;
  tone?: ChipTone;
  className?: string;
}

export function Chip({ children, onRemove, tone = "neutral", className = "" }: ChipProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[12.5px] font-medium ring-1 ring-inset",
        "transition-all duration-200 ease-ios",
        TONE[tone],
        className,
      ].join(" ")}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove"
          className="ml-0.5 grid h-4 w-4 place-items-center rounded-md text-current opacity-50 transition-opacity duration-150 ease-ios hover:bg-black/5 hover:opacity-100"
        >
          <X size={11} strokeWidth={2.5} />
        </button>
      )}
    </span>
  );
}
