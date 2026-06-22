"use client";
import { CheckCircle2, XCircle, Loader2, AlertTriangle, Clock } from "lucide-react";
import { type EngineResult } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  EngineResult["status"],
  { icon: any; label: string; cls: string }
> = {
  pending:  { icon: Clock,          label: "Queued",    cls: "text-text-subtle" },
  running:  { icon: Loader2,        label: "Scanning",  cls: "text-accent animate-spin" },
  clean:    { icon: CheckCircle2,   label: "Clean",     cls: "text-success" },
  detected: { icon: XCircle,        label: "Detected",  cls: "text-danger" },
  error:    { icon: AlertTriangle,  label: "Error",     cls: "text-warn" },
  timeout:  { icon: AlertTriangle,  label: "Timeout",   cls: "text-warn" },
};

export function ResultsTable({ results }: { results: EngineResult[] }) {
  const sorted = [...results].sort((a, b) => {
    const order = { detected: 0, error: 1, timeout: 2, clean: 3, running: 4, pending: 5 } as const;
    return order[a.status] - order[b.status] || a.engine_name.localeCompare(b.engine_name);
  });

  return (
    <div className="card overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-bg-elevated/60 text-left text-text-muted text-xs uppercase tracking-wider">
            <th className="px-4 py-3 font-medium">Engine</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Detection</th>
            <th className="px-4 py-3 font-medium hidden md:table-cell">Definitions</th>
            <th className="px-4 py-3 font-medium text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const meta = STATUS_META[r.status];
            const Icon = meta.icon;
            return (
              <tr key={r.engine_id} className="border-t border-border/60 hover:bg-bg-elevated/30">
                <td className="px-4 py-3">
                  <div className="font-medium">{r.engine_name}</div>
                  <div className="text-xs text-text-subtle">{r.vendor}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={cn("inline-flex items-center gap-1.5", meta.cls)}>
                    <Icon size={14} />
                    <span className="text-xs font-medium">{meta.label}</span>
                  </span>
                </td>
                <td className="px-4 py-3 max-w-xs">
                  {r.status === "detected" && r.detection_name ? (
                    <span className="font-mono text-danger text-xs">
                      {r.detection_name}
                    </span>
                  ) : r.status === "clean" ? (
                    <span className="text-text-subtle text-xs">—</span>
                  ) : r.status === "error" || r.status === "timeout" ? (
                    <span className="text-warn text-xs truncate block" title={r.error_message || ""}>
                      {r.error_message || meta.label}
                    </span>
                  ) : (
                    <span className="text-text-subtle text-xs">…</span>
                  )}
                </td>
                <td className="px-4 py-3 hidden md:table-cell text-xs text-text-muted font-mono">
                  {r.definitions_version || "—"}
                </td>
                <td className="px-4 py-3 text-right text-xs text-text-muted font-mono">
                  {r.duration_ms ? `${(r.duration_ms / 1000).toFixed(1)}s` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
