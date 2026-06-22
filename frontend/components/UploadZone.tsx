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
          "card border-2 border-dashed p-10 text-center cursor-pointer transition-all",
          isDragActive
            ? "border-accent bg-accent/5 shadow-glow"
            : "border-border hover:border-border-strong",
          submitting && "pointer-events-none opacity-60"
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          {submitting ? (
            <Loader2 className="text-accent animate-spin" size={48} />
          ) : (
            <UploadCloud className="text-accent" size={48} />
          )}
          {file ? (
            <div>
              <div className="font-medium">{file.name}</div>
              <div className="text-sm text-text-muted">{formatBytes(file.size)}</div>
              {submitting && uploadPct !== undefined && (
                <div className="mt-3 w-64 mx-auto">
                  <div className="h-1.5 bg-bg-elevated rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent transition-all"
                      style={{ width: `${uploadPct}%` }}
                    />
                  </div>
                  <div className="text-xs text-text-subtle mt-1">{uploadPct}%</div>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="text-lg font-medium">
                {isDragActive ? "Drop the file here" : "Drag & drop a file, or click to select"}
              </div>
              <div className="text-sm text-text-muted max-w-md">
                EXE, DLL, SCR, COM, PS1, MSI, scripts, Office docs, archives — up to{" "}
                {formatBytes(MAX_BYTES)}. Files are quarantined and only executed inside
                isolated AV VMs.
              </div>
            </>
          )}
        </div>
      </div>
      {error && (
        <div className="mt-3 flex items-center gap-2 text-danger text-sm bg-danger-soft/40 border border-danger/30 px-3 py-2 rounded-lg">
          <FileWarning size={16} /> {error}
        </div>
      )}
    </div>
  );
}
