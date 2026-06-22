import "./globals.css";
import type { Metadata } from "next";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "FileScan — Multi-AV malware analysis",
  description:
    "Submit a file and have it scanned by multiple antivirus engines in parallel inside isolated VMs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-border py-6 text-center text-xs text-text-subtle">
          FileScan · isolated VM scanning · all uploads auto-shredded after analysis
        </footer>
      </body>
    </html>
  );
}
