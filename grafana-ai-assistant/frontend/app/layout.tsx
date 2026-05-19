import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Grafana AI Assistant",
  description: "Prompt to Grafana JSON with Prometheus context"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
