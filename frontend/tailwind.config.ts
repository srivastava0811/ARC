import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        accent: "#147efb",
      },
    },
  },
  plugins: [],
};

export default config;
