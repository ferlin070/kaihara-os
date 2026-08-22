/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        kaihara: {
          bg: "#0a0e1a",
          surface: "#111827",
          border: "#1f2937",
          primary: "#3b82f6",
          accent: "#06b6d4",
          success: "#10b981",
          warning: "#f59e0b",
          danger: "#ef4444",
          text: "#e5e7eb",
          muted: "#6b7280",
        }
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "ping-slow": "ping 2s cubic-bezier(0, 0, 0.2, 1) infinite",
      }
    },
  },
  plugins: [],
}
