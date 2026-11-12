import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keeps ARC's active development server independent from any stale local Next process.
  distDir: ".next-arc",
  // ARC supplies its own preview branding, so hide the Next.js development badge.
  devIndicators: false,
};

export default nextConfig;
