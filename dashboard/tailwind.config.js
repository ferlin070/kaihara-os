/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        kaihara: {
          bg: "#0f0f0f",
          surface: "#1a1a1a",
          card: "#1e1e1e",
          border: "#2a2a2a",
          hover: "#252525",
          primary: "#8b5cf6",
          accent: "#a78bfa",
          success: "#22c55e",
          warning: "#eab308",
          danger: "#ef4444",
          text: "#f5f5f5",
          muted: "#737373",
          subtle: "#525252",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(139, 92, 246, 0.15)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.3)',
      },
      animation: {
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "ping-slow": "ping 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
}
