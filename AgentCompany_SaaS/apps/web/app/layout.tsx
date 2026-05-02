import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentCompany",
  description: "Multi-tenant AI agent workspaces"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
