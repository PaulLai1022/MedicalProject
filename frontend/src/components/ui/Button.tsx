import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  fullWidth?: boolean;
}

const VARIANT: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white shadow-soft hover:bg-brand-700 hover:shadow-lift active:bg-brand-800",
  secondary:
    "bg-white text-ink-800 border border-ink-200 shadow-soft hover:bg-ink-50 hover:border-ink-300",
  ghost:
    "text-ink-700 hover:bg-ink-100 active:bg-ink-200",
  danger:
    "bg-admit-600 text-white shadow-soft hover:bg-admit-700",
};

const SIZE: Record<Size, string> = {
  sm: "h-8  px-3   text-[13px] gap-1.5 rounded-lg",
  md: "h-10 px-4   text-[14px] gap-2   rounded-xl",
  lg: "h-12 px-5.5 text-[15px] gap-2   rounded-xl2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    iconLeft,
    iconRight,
    fullWidth = false,
    children,
    className = "",
    disabled,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={[
        "inline-flex items-center justify-center font-medium tracking-tight",
        "transition-all duration-200 ease-ios",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:shadow-none",
        VARIANT[variant],
        SIZE[size],
        fullWidth ? "w-full" : "",
        className,
      ].join(" ")}
      {...rest}
    >
      {loading ? (
        <Spinner />
      ) : (
        iconLeft && <span className="-ml-0.5 inline-flex">{iconLeft}</span>
      )}
      {children}
      {!loading && iconRight && <span className="-mr-0.5 inline-flex">{iconRight}</span>}
    </button>
  );
});

function Spinner() {
  return (
    <svg
      className="animate-spin"
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.28" strokeWidth="3" />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
