/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        brand: {
          DEFAULT: "#6366F1",
          hover:   "#4F46E5",
          muted:   "#6366F120",
        },
        // Map zinc to CSS custom properties so dark/light themes work
        // via a single class toggle on <html>. Alpha modifiers (bg-zinc-900/10)
        // work because we use RGB triplets with <alpha-value> placeholder.
        zinc: {
          50:  "rgb(var(--zinc-50)  / <alpha-value>)",
          100: "rgb(var(--zinc-100) / <alpha-value>)",
          200: "rgb(var(--zinc-200) / <alpha-value>)",
          300: "rgb(var(--zinc-300) / <alpha-value>)",
          400: "rgb(var(--zinc-400) / <alpha-value>)",
          500: "rgb(var(--zinc-500) / <alpha-value>)",
          600: "rgb(var(--zinc-600) / <alpha-value>)",
          700: "rgb(var(--zinc-700) / <alpha-value>)",
          800: "rgb(var(--zinc-800) / <alpha-value>)",
          900: "rgb(var(--zinc-900) / <alpha-value>)",
          950: "rgb(var(--zinc-950) / <alpha-value>)",
        },
      },
      animation: {
        "fade-in":   "fadeIn 0.15s ease-out",
        "slide-up":  "slideUp 0.2s ease-out",
        "pulse-dot": "pulseDot 2s ease-in-out infinite",
        "spin-slow": "spin 2s linear infinite",
      },
      keyframes: {
        fadeIn:   { "0%": { opacity: 0 }, "100%": { opacity: 1 } },
        slideUp:  { "0%": { opacity: 0, transform: "translateY(8px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        pulseDot: { "0%,100%": { opacity: 1 }, "50%": { opacity: 0.4 } },
        bounce:   { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-5px)" } },
      },
    },
  },
  plugins: [],
};
