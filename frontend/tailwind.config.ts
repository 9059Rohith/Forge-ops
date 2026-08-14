import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#060b10",
        panel: "#0b141c",
        surface: "#101b24",
        line: "#263844",
        ink: "#f4f7f6",
        muted: "#94a3ad",
        mint: "#64e6bd",
        amber: "#f4b74a",
        danger: "#ff6b70"
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "Inter", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      boxShadow: { panel: "0 20px 60px rgba(0,0,0,.28)" }
    }
  },
  plugins: []
};

export default config;

