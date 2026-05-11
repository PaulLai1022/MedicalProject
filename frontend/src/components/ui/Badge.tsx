import type { ReactNode } from "react";

export type Tone =
  | "admit"
  | "observe"
  | "discharge"
  | "unknown"
  | "brand"
  | "edited"
  | "neutral";

type Size = "sm" | "md" | "lg";

interface BadgeProps {
  tone?: Tone;
  size?: Size;
  dot?: boolean;
  icon?: ReactNode;
  className?: string;
  children: ReactNode;
}

const BG: Record<Tone, string> = {
  admit:     "bg-admit-100     text-admit-700     ring-admit-100",
  observe:   "bg-observe-100   text-observe-700   ring-observe-100",
  discharge: "bg-discharge-100 text-discharge-700 ring-discharge-100",
  unknown:   "bg-unknown-100   text-unknown-700   ring-unknown-100",
  brand:     "bg-brand-100     text-brand-700     ring-brand-100",
  edited:    "bg-edited-100    text-edited-700    ring-edited-100",
  neutral:   "bg-ink-100       text-ink-700       ring-ink-200",
};

const DOT: Record<Tone, string> = {
  admit:     "bg-admit-600",
  observe:   "bg-observe-600",
  discharge: "bg-discharge-600",
  unknown:   "bg-unknown-600",
  brand:     "bg-brand-600",
  edited:    "bg-edited-600",
  neutral:   "bg-ink-500",
};

const SIZE: Record<Size, string> = {
  sm: "h-5  px-1.5 text-[10.5px] gap-1   rounded-md",
  md: "h-6  px-2   text-[11.5px] gap-1.5 rounded-lg",
  lg: "h-9  px-3   text-[13px]   gap-2   rounded-xl",
};

export function Badge({
  tone = "neutral",
  size = "md",
  dot,
  icon,
  className = "",
  children,
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center font-medium ring-1 ring-inset",
        BG[tone],
        SIZE[size],
        className,
      ].join(" ")}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${DOT[tone]}`} />}
      {icon}
      {children}
    </span>
  );
}
