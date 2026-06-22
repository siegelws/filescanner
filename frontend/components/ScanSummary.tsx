"use client";
import { ShieldCheck, ShieldAlert, ShieldX, FileText, Hash } from "lucide-react";
import { type ScanDetail } from "@/lib/api";
import { cn, formatBytes } from "@/lib/utils";

export function ScanSummary({ scan }: { scan: ScanDetail }) {
  const detections = scan.detections;
  const total = scan.engines_requested;
  const verdict =
    scan.status !== "completed"
      ? "pending"
      : detections === 0
      ? "clean"
      : detections >= Math.ceil(total / 2)
      ? "malicious"
      : "suspicious";

  const themes = {
    clean: {
      icon: ShieldCheck,
      label: "Clean",
      tint: "bg-success-soft border-success-border text-success",
      ring: "ring-success-border/60",
      glow: "shadow-soft",
    },
    suspicious: {
      icon: ShieldAlert,
      label: "Suspicious",
      tint: "bg-warn-soft border-warn-border text-warn",
      ring: "ring-warn-border/60",
      glow: "shadow-gold",
    },
    malicious: {
      icon: ShieldX,
      label: "Malicious",
      tint: "bg-danger-soft border-danger-border text-danger",
      ring: "ring-danger-border/60",
      glow: "shadow-pink",
    },
    pending: {
      icon: ShieldAlert,
      label: "Pending",
      tint: "bg-bg-elevated border-border text-text-muted",
      ring: "ring-border",
      glow: "shadow-soft",
    },
  } as const;

  const v = themes[verdict];
  const Icon = v.icon;

  return (
    <div className={cn("card p-7 ring-1 relative overflow-hidden", v.ring, v.glow)}>
      <div
        className="pointer-events-none absolute -top-12 -right-12 w-64 h-64 rounded-full opacity-40"
        style={{
          background:
            verdict === "malicious"
              ? "radial-gradient(circle, rgba(236,79,156,0.35) 0%, transparent 70%)"
              : "radial-gradient(circle, rgba(240,214,138,0.5) 0%, transparent 70%)",
        }}
      />
      <div className="relative flex items-start gap-5">
        <div className={cn("p-4 rounded-2xl border", v.tint)}>
          <Icon size={36} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3 flex-wrap">
            <h2 className="font-display text-3xl font-semibold">{v.label}</h2>
            <span className="text-text-muted text-sm">
              Detected by{" "}
              <span className="text-text font-mono font-bold">
                {detections}/{total}
              </span>{" "}
              engines
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-sm text-text-muted">
            <FileText size={14} />
            <span className="truncate font-medium text-text">{scan.filename}</span>
            <span className="text-text-subtle">· {formatBytes(scan.file_size)}</span>
            {scan.mime_type && (
              <span className="text-text-subtle">· {scan.mime_type}</span>
            )}
          </div>
          <div className="mt-3 grid sm:grid-cols-3 gap-x-6 gap-y-1 text-xs font-mono">
            <HashRow label="MD5" value={scan.md5} />
            <HashRow label="SHA1" value={scan.sha1} />
            <HashRow label="SHA256" value={scan.sha256} />
          </div>
        </div>
      </div>
    </div>
  );
}

function HashRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <Hash size={11} className="text-accent shrink-0" />
      <span className="text-text-subtle font-semibold">{label}</span>
      <span className="truncate text-text-muted">{value}</span>
    </div>
  );
}
