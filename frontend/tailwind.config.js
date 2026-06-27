/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#04060c",
        abyss: "#070b16",
        navy: "#0b1426",
        panel: "#0d1830",
        brass: "#d4a44a",
        ember: "#f3d27a",
        gold: "#e7c071",
        line: "rgba(212, 164, 74, 0.16)",
        mist: "#94a3b8",
        success: "#4ade80",
        warning: "#f59e0b",
        danger: "#f87171",
      },
      fontFamily: {
        display: ['"Instrument Serif"', "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(212, 164, 74, 0.14), 0 30px 90px rgba(2, 6, 14, 0.7)",
        brass: "0 0 40px rgba(212, 164, 74, 0.18)",
      },
      animation: {
        "fade-in": "fade-in 0.5s ease-out both",
        "fade-up": "fade-up 0.6s cubic-bezier(0.16,1,0.3,1) both",
        "scale-in": "scale-in 0.4s cubic-bezier(0.16,1,0.3,1) both",
        breathe: "breathe 4s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
        "spin-slow": "spin 18s linear infinite",
      },
      keyframes: {
        "fade-in": { from: { opacity: 0 }, to: { opacity: 1 } },
        "fade-up": {
          from: { opacity: 0, transform: "translateY(12px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: 0, transform: "scale(0.96)" },
          to: { opacity: 1, transform: "scale(1)" },
        },
        breathe: {
          "0%,100%": { opacity: 0.6, transform: "scale(1)" },
          "50%": { opacity: 1, transform: "scale(1.04)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
