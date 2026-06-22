import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0a0d12",
          subtle: "#10141b",
          surface: "#161b24",
          elevated: "#1c2230",
        },
        border: { DEFAULT: "#232a38", strong: "#2e3648" },
        text: { DEFAULT: "#e6edf6", muted: "#94a3b8", subtle: "#64748b" },
        accent: {
          DEFAULT: "#22d3ee",   // cyan-400
          hover: "#06b6d4",
          glow: "#0e7490",
        },
        danger: { DEFAULT: "#f43f5e", soft: "#3a1a23" },
        success: { DEFAULT: "#34d399", soft: "#0f2a23" },
        warn: { DEFAULT: "#facc15", soft: "#3a2e0d" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34, 211, 238, 0.25), 0 8px 32px -8px rgba(34, 211, 238, 0.2)",
      },
      animation: {
        "pulse-glow": "pulse-glow 2.5s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(34, 211, 238, 0.4)" },
          "50%": { boxShadow: "0 0 0 12px rgba(34, 211, 238, 0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
