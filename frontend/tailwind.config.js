/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50:  "#F8FAFC",
          100: "#EEF2F6",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#94A3B8",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1F2937",
          900: "#0B0F14",
        },
        brand: {
          50:  "#F2F7FF",
          100: "#E6F0FF",
          200: "#C9DEFF",
          300: "#9CC2FF",
          400: "#5C9DFF",
          500: "#2B7FFF",
          600: "#0A6CFF",
          700: "#0852C7",
          800: "#073F95",
        },
        admit:     { 50: "#FEF2F2", 100: "#FEE2E2", 600: "#DC2626", 700: "#B91C1C" },
        observe:   { 50: "#FFFBEB", 100: "#FEF3C7", 600: "#D97706", 700: "#B45309" },
        discharge: { 50: "#ECFDF5", 100: "#D1FAE5", 600: "#059669", 700: "#047857" },
        unknown:   { 50: "#F8FAFC", 100: "#F1F5F9", 600: "#64748B", 700: "#475569" },
        edited:    { 50: "#F5F3FF", 100: "#EDE9FE", 600: "#7C3AED", 700: "#6D28D9" },
      },
      fontFamily: {
        sans: [
          '"SF Pro Text"',
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Inter",
          '"PingFang SC"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
        display: [
          '"SF Pro Display"',
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          '"PingFang SC"',
          "sans-serif",
        ],
        mono: [
          '"SF Mono"',
          '"JetBrains Mono"',
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        "display-lg": ["44px", { lineHeight: "1.1", letterSpacing: "-0.022em", fontWeight: "700" }],
        "display":    ["36px", { lineHeight: "1.15", letterSpacing: "-0.02em",  fontWeight: "700" }],
        "title":      ["22px", { lineHeight: "1.3",  letterSpacing: "-0.01em",  fontWeight: "600" }],
        "subtitle":   ["17px", { lineHeight: "1.4",  letterSpacing: "-0.005em", fontWeight: "600" }],
      },
      borderRadius: {
        "xl2":  "14px",
        "2xl2": "18px",
        "3xl2": "22px",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(15,23,42,0.04), 0 1px 1px rgba(15,23,42,0.03)",
        card: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
        lift: "0 8px 24px rgba(15,23,42,0.08), 0 2px 6px rgba(15,23,42,0.04)",
        ring: "0 0 0 4px rgba(10,108,255,0.18)",
      },
      transitionTimingFunction: {
        ios: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
      transitionDuration: {
        250: "250ms",
        350: "350ms",
      },
      backdropBlur: {
        xs: "2px",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s cubic-bezier(0.32, 0.72, 0, 1) both",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
};
