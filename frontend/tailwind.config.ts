import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Pearl-white surfaces with subtle champagne warmth
        bg: {
          DEFAULT:  "#fdfaf5",   // warm pearl white — page background
          subtle:   "#f7f0e6",   // champagne — section bands
          surface:  "#ffffff",   // pure white — cards
          elevated: "#fefbf4",   // cream — table rows / inner panels
        },
        border: {
          DEFAULT:  "#efe2cc",   // soft champagne border
          strong:   "#e5cda6",   // warm gold-tinted border
        },
        text: {
          DEFAULT:  "#231a12",   // deep espresso for primary text
          muted:    "#6f5c48",   // warm taupe for secondary
          subtle:   "#a99785",   // light champagne grey
        },

        // GOLD — primary accent
        accent: {
          DEFAULT: "#c9a13c",     // rich champagne gold
          hover:   "#b88a25",     // darker gold for hover
          soft:    "#fbf2dc",     // very soft gold wash
          glow:    "#f0d68a",     // bright gold glow
        },
        gold: {
          50:  "#fdf8e9",
          100: "#faeec5",
          200: "#f5dd95",
          300: "#eac658",
          400: "#d8ad32",
          500: "#c9a13c",
          600: "#a68023",
          700: "#80631d",
          800: "#594516",
          900: "#3a2d10",
        },

        // PINK — secondary accent / highlights
        pink: {
          DEFAULT: "#ec4f9c",     // bright rose pink
          hover:   "#d6388a",
          soft:    "#fde5ef",     // blush wash
          glow:    "#f7b8d6",
          deep:    "#9d2d6a",
        },
        rose: {
          50:  "#fef3f7",
          100: "#fde5ef",
          200: "#fbcadf",
          300: "#f79bc4",
          400: "#f070a8",
          500: "#ec4f9c",
          600: "#d2398c",
          700: "#a72674",
          800: "#76165a",
          900: "#480c3a",
        },

        // Status colors retuned to harmonise with the warm palette
        danger:  { DEFAULT: "#e11d48", soft: "#fde0e6", border: "#f6a8b8" },
        success: { DEFAULT: "#15803d", soft: "#dcf3e3", border: "#86d6a4" },
        warn:    { DEFAULT: "#b88a25", soft: "#fbf2dc", border: "#e8c97a" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Playfair Display"', "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        soft:    "0 4px 16px -4px rgba(184, 138, 37, 0.10), 0 2px 4px -2px rgba(184, 138, 37, 0.05)",
        gold:    "0 8px 28px -10px rgba(201, 161, 60, 0.55), 0 0 0 1px rgba(201, 161, 60, 0.30)",
        pink:    "0 8px 28px -10px rgba(236, 79, 156, 0.45), 0 0 0 1px rgba(236, 79, 156, 0.25)",
        pop:     "0 12px 32px -12px rgba(231, 184, 88, 0.4), 0 6px 12px -8px rgba(236, 79, 156, 0.18)",
        innerSoft: "inset 0 1px 0 rgba(255, 255, 255, 0.65)",
      },
      backgroundImage: {
        "gold-gradient":  "linear-gradient(135deg, #f0d68a 0%, #c9a13c 50%, #a68023 100%)",
        "pink-gradient":  "linear-gradient(135deg, #f7b8d6 0%, #ec4f9c 60%, #a72674 100%)",
        "lux-gradient":   "linear-gradient(135deg, #f0d68a 0%, #ec4f9c 100%)",
        "page-radial":    "radial-gradient(1100px 600px at 5% -10%, rgba(247,184,214,0.35) 0%, transparent 60%), radial-gradient(900px 500px at 95% 0%, rgba(240,214,138,0.40) 0%, transparent 55%)",
      },
      animation: {
        "pulse-gold": "pulse-gold 2.6s ease-in-out infinite",
        "shimmer":    "shimmer 3s linear infinite",
      },
      keyframes: {
        "pulse-gold": {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(201, 161, 60, 0.45)" },
          "50%":     { boxShadow: "0 0 0 14px rgba(201, 161, 60, 0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
