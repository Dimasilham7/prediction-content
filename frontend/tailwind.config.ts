import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#12151a",
        mist: "#e8edf2",
        sea: "#0f6e8c",
        coral: "#c45c26",
        moss: "#2f6b4f",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
