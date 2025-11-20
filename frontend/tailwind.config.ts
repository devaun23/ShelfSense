import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1E3A5F',
          light: '#2C5282',
          dark: '#0F1E3F',
        },
      },
      backgroundColor: {
        primary: '#000000',
      },
      textColor: {
        primary: '#FFFFFF',
      },
    },
  },
  plugins: [],
};

export default config;
