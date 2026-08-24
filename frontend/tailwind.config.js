/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "Helvetica", "Arial", "sans-serif"],
      },
      colors: {
        canvas: "var(--canvas)",
        surface: "var(--surface)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        edge: "var(--edge)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          fg: "var(--accent-fg)",
          soft: "var(--accent-soft)",
        },
        sidebar: {
          DEFAULT: "var(--sidebar)",
          ink: "var(--sidebar-ink)",
          muted: "var(--sidebar-muted)",
          hover: "var(--sidebar-hover)",
          active: "var(--sidebar-active)",
        },
      },
    },
  },
  plugins: [],
};
