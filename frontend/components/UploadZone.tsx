"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FileWarning, Loader2 } from "lucide-react";
import { cn, formatBytes } from "@/lib/utils";

const ALLOWED_EXT = new Set([
  ".exe", ".dll", ".scr", ".com", ".sys", ".cpl", ".msi",
  ".ps1", ".bat", ".cmd", ".vbs", ".js", ".jse", ".wsf",
  ".jar", ".apk", ".elf", ".bin",
  ".doc", ".docx", ".docm", ".xls", ".xlsx", ".xlsm",
  ".ppt", ".pptx", ".pdf", ".rtf",
  ".zip", ".rar", ".7z", ".tar", ".gz",
]);
const MAX_BYTES = 200 * 1024 * 1024;

interface Props {
  file: File | null;
  onFile: (f: File | null) => void;
  submitting?: boolean;
  uploadPct?: number;
}

export function UploadZone({ file, onFile, submitting, uploadPct }: Props) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[], rejected: any[]) => {
      setError(null);
      if (rejected.length) {
        setError("File rejected — wrong type or too large.");
        return;
      }
      const f = accepted[0];
      if (!f) return;
      const dot = f.name.lastIndexOf(".");
      const ext = dot >= 0 ? f.name.slice(dot).toLowerCase() : "";
      if (!ALLOWED_EXT.has(ext)) {
        setError(`Extension '${ext || "(none)"}' is not supported.`);
        return;
      }
      if (f.size > MAX_BYTES) {
        setError(`File is ${formatBytes(f.size)} — limit is ${formatBytes(MAX_BYTES)}.`);
        return;
      }
      onFile(f);
    },
    [onFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    maxSize: MAX_BYTES,
    disabled: submitting,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          "relative card border-2 border-dashed p-12 text-center cursor-pointer transition-all overflow-hidden",
          isDragActive
            ? "border-accent bg-accent-soft shadow-pop"
            : "border-border hover:border-accent hover:shadow-pop",
          submitting && "pointer-events-none opacity-70"
        )}
      >
        {/* subtle radial glow under drop zone */}
        <div className="pointer-events-none absolute inset-0 opacity-60"
             style={{ background: "radial-gradient(500px 200px at 50% -10%, rgba(247,184,214,0.25), transparent 70%)" }} />
        <input {...getInputProps()} />
        <div className="relative flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gold-gradient flex items-center justify-center shadow-gold">
            {submitting ? (
              <Loader2 className="text-white animate-spin" size={28} />
            ) : (
              <UploadCloud className="text-white" size={28} />
            )}
          </div>
          {file ? (
            <div>
              <div className="font-display text-xl">{file.name}</div>
              <div className="text-sm text-text-muted">{formatBytes(file.size)}</div>
              {submitting && uploadPct !== undefined && (
                <div className="mt-4 w-72 mx-auto">
                  <div className="h-2 bg-bg-elevated rounded-full overflow-hidden border border-border">
                    <div
                      className="h-full bg-gold-gradient transition-all"
                      style={{ width: `${uploadPct}%` }}
                    />
                  </div>
                  <div className="text-xs text-text-subtle mt-2">{uploadPct}% uploaded</div>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="font-display text-2xl">
                {isDragActive ? "Drop the file here" : "Drag & drop your file"}
              </div>
              <div className="text-sm text-text-muted max-w-md">
                Or click anywhere in this box to select one. EXE, DLL, PS1, MSI,
                Office docs, PDFs, archives — up to {formatBytes(MAX_BYTES)}.
                <br />
                <span className="text-text-subtle">Files are scanned in isolated containers, never executed on this host.</span>
              </div>
            </>
          )}
        </div>
      </div>
      {error && (
        <div className="mt-3 flex items-center gap-2 text-danger text-sm bg-danger-soft border border-danger-border px-3 py-2 rounded-xl">
          <FileWarning size={16} /> {error}
        </div>
      )}
    </div>
  );
}
