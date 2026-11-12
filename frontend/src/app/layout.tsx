import type { Metadata } from "next";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "ARC — Procurement workspace",
  description: "From intent to transaction.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
