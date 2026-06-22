"use client";
import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  Clock,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import {
  parseBreakdown,
  type EngineResult,
  type SubEngine,
  type SubEngineBreakdown,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_META: Record<
  EngineResult["status"],
  { icon: any; label: string; cls: string }
> = {
  pending:  { icon: Clock,         label: "Queued",   cls: "text-text-subtle" },
  running:  { icon: Loader2,       label: "Scanning", cls: "text-accent animate-spin" },
  clean:    { icon: CheckCircle2,  label: "Clean",    cls: "text-success" },
  detected: { icon: XCircle,       label: "Detected", cls: "text-danger" },
  error:    { icon: AlertTriangle, label: "Error",    cls: "text-warn" },
  timeout:  { icon: AlertTriangle, label: "Timeout",  cls: "text-warn" },
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
            <th className="px-4 py-3 font-medium w-8"></th>
            <th className="px-4 py-3 font-medium">Engine</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Detection</th>
            <th className="px-4 py-3 font-medium hidden md:table-cell">Definitions</th>
            <th className="px-4 py-3 font-medium text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <EngineRow key={r.engine_id} result={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EngineRow({ result }: { result: EngineResult }) {
  const meta = STATUS_META[result.status];
  const Icon = meta.icon;
  const breakdown = parseBreakdown(result);
  const expandable = !!breakdown && breakdown.engines.length > 0;

  const [open, setOpen] = useState(false);

  return (
    <>
      <tr
        className={cn(
          "border-t border-border/60",
          expandable ? "hover:bg-bg-elevated/40 cursor-pointer" : "hover:bg-bg-elevated/30"
        )}
        onClick={() => expandable && setOpen((v) => !v)}
      >
        <td className="px-4 py-3 text-text-subtle">
          {expandable ? (
            open ? (
              <ChevronDown size={16} className="text-accent" />
            ) : (
              <ChevronRight size={16} />
            )
          ) : (
            <span className="inline-block w-4" />
          )}
        </td>
        <td className="px-4 py-3">
          <div className="font-medium">{result.engine_name}</div>
          <div className="text-xs text-text-subtle">{result.vendor}</div>
        </td>
        <td className="px-4 py-3">
          <span className={cn("inline-flex items-center gap-1.5", meta.cls)}>
            <Icon size={14} />
            <span className="text-xs font-medium">{meta.label}</span>
          </span>
        </td>
        <td className="px-4 py-3 max-w-xs">
          {result.status === "detected" && result.detection_name ? (
            <span className="font-mono text-danger text-xs">{result.detection_name}</span>
          ) : result.status === "clean" ? (
            <span className="text-text-subtle text-xs">—</span>
          ) : result.status === "error" || result.status === "timeout" ? (
            <span
              className="text-warn text-xs truncate block"
              title={result.error_message || ""}
            >
              {result.error_message || meta.label}
            </span>
          ) : (
            <span className="text-text-subtle text-xs">…</span>
          )}
          {expandable && (
            <div className="text-xs text-text-subtle mt-0.5">
              {summariseBreakdown(breakdown!)}
              <span className="ml-2 text-accent">{open ? "hide" : "click to expand"}</span>
            </div>
          )}
        </td>
        <td className="px-4 py-3 hidden md:table-cell text-xs text-text-muted font-mono">
          {result.definitions_version || "—"}
        </td>
        <td className="px-4 py-3 text-right text-xs text-text-muted font-mono">
          {result.duration_ms ? `${(result.duration_ms / 1000).toFixed(1)}s` : "—"}
        </td>
      </tr>
      {expandable && open && (
        <tr className="bg-bg-subtle/60">
          <td colSpan={6} className="px-0 py-0">
            <SubEngineTable engines={breakdown!.engines} />
          </td>
        </tr>
      )}
    </>
  );
}

function summariseBreakdown(b: SubEngineBreakdown): string {
  const mal = Number(b.stats?.malicious || 0);
  const susp = Number(b.stats?.suspicious || 0);
  const total = Number(b.stats?.total || b.engines.length);
  return `${mal + susp}/${total} engines flagged`;
}

function SubEngineTable({ engines }: { engines: SubEngine[] }) {
  return (
    <div className="max-h-96 overflow-y-auto border-y border-border/60">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-bg-subtle">
          <tr className="text-left text-text-subtle text-[10px] uppercase tracking-wider">
            <th className="px-4 py-2 font-medium w-1/3">Engine</th>
            <th className="px-4 py-2 font-medium w-24">Verdict</th>
            <th className="px-4 py-2 font-medium">Detection</th>
          </tr>
        </thead>
        <tbody>
          {engines.map((e, i) => {
            const cls = categoryColor(e.category);
            return (
              <tr key={`${e.engine}-${i}`} className="border-t border-border/40 hover:bg-bg-elevated/20">
                <td className="px-4 py-1.5 font-medium">{e.engine}</td>
                <td className={cn("px-4 py-1.5 font-medium uppercase text-[10px]", cls)}>
                  {labelOf(e.category)}
                </td>
                <td className="px-4 py-1.5 font-mono">
                  {e.detection ? (
                    <span className={cls}>{e.detection}</span>
                  ) : (
                    <span className="text-text-subtle">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function categoryColor(c: string): string {
  switch (c) {
    case "malicious": return "text-danger";
    case "suspicious": return "text-warn";
    case "harmless":
    case "undetected": return "text-text-muted";
    case "type-unsupported":
    case "timeout":
    case "failure": return "text-text-subtle";
    default: return "text-text-subtle";
  }
}

function labelOf(c: string): string {
  switch (c) {
    case "malicious": return "Detected";
    case "suspicious": return "Suspicious";
    case "harmless":
    case "undetected": return "Clean";
    case "type-unsupported": return "N/A";
    case "timeout": return "Timeout";
    case "failure": return "Error";
    default: return c;
  }
}
