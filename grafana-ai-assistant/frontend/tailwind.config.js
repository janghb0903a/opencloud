/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#06090f",
        panel: "#0f1724",
        line: "#1f2d44",
        accent: "#00d4b8",
        muted: "#9db3c7"
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(0, 212, 184, 0.35), 0 8px 40px rgba(0, 0, 0, 0.35)"
      }
    }
  },
  plugins: [],
};
