"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck, ShieldX, ShieldAlert, Clock } from "lucide-react";
import { api, getToken, type ScanSummary } from "@/lib/api";
import { formatBytes, relativeTime, shortHash } from "@/lib/utils";
import { cn } from "@/lib/utils";

export default function HistoryPage() {
  const router = useRouter();
  const [scans, setScans] = useState<ScanSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login?next=/history");
      return;
    }
    api.listScans().then(setScans).catch((e) => setError(e.message));
  }, [router]);

  if (error)
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-danger">
        {error}
      </div>
    );

  if (!scans)
    return (
      <div className="max-w-3xl mx-auto px-4 py-24 flex items-center justify-center gap-3 text-text-muted">
        <Loader2 className="animate-spin text-accent" size={20} /> Loading history…
      </div>
    );

  if (!scans.length)
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-text-muted">
        No scans yet —{" "}
        <Link href="/" className="text-accent underline">
          submit your first file
        </Link>
        .
      </div>
    );

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Your scan history</h1>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-bg-elevated/60 text-left text-text-muted text-xs uppercase tracking-wider">
              <th className="px-4 py-3 font-medium">File</th>
              <th className="px-4 py-3 font-medium">SHA256</th>
              <th className="px-4 py-3 font-medium">Verdict</th>
              <th className="px-4 py-3 font-medium text-right">When</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => (
              <ScanRow key={s.id} scan={s} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScanRow({ scan }: { scan: ScanSummary }) {
  const verdict = verdictOf(scan);
  return (
    <tr className="border-t border-border/60 hover:bg-bg-elevated/30">
      <td className="px-4 py-3">
        <Link href={`/scan/${scan.id}`} className="font-medium hover:text-accent">
          {scan.filename}
        </Link>
        <div className="text-xs text-text-subtle">{formatBytes(scan.file_size)}</div>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-text-muted">
        {shortHash(scan.sha256, 16)}
      </td>
      <td className="px-4 py-3">
        <span className={cn("pill", verdict.cls)}>
          <verdict.icon size={12} />
          {verdict.label}
          <span className="text-text-subtle font-mono ml-1">
            {scan.detections}/{scan.engines_requested}
          </span>
        </span>
      </td>
      <td className="px-4 py-3 text-right text-xs text-text-muted">
        {relativeTime(scan.created_at)}
      </td>
    </tr>
  );
}

function verdictOf(s: ScanSummary) {
  if (s.status !== "completed")
    return { icon: Clock, label: "In progress", cls: "border-border text-text-muted bg-bg-elevated" };
  if (s.detections === 0)
    return { icon: ShieldCheck, label: "Clean", cls: "border-success/40 text-success bg-success-soft/30" };
  if (s.detections >= Math.ceil(s.engines_requested / 2))
    return { icon: ShieldX, label: "Malicious", cls: "border-danger/40 text-danger bg-danger-soft/30" };
  return { icon: ShieldAlert, label: "Suspicious", cls: "border-warn/40 text-warn bg-warn-soft/30" };
}
