import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MCP Trace Studio",
  description: "Local-first observability for MCP agents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
