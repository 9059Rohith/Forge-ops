import type { Metadata } from "next";
import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "ForgeGuard — Autonomous engineering, with proof",
  description: "Verification, repair, and evidence for autonomous code changes.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
