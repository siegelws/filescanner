/* Lightweight typed client for the FastAPI backend. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type EngineStatus = "pending" | "running" | "clean" | "detected" | "error" | "timeout";

export interface EngineInfo {
  id: string;
  name: string;
  vendor: string;
  enabled: boolean;
}

export interface EngineResult {
  engine_id: string;
  engine_name: string;
  vendor: string;
  status: EngineStatus;
  detection_name: string | null;
  engine_version: string | null;
  definitions_version: string | null;
  duration_ms: number | null;
  error_message: string | null;
  completed_at: string | null;
}

export type ScanStatus = "queued" | "running" | "completed" | "failed";

export interface ScanSummary {
  id: string;
  filename: string;
  file_size: number;
  md5: string;
  sha256: string;
  status: ScanStatus;
  engines_requested: number;
  engines_completed: number;
  detections: number;
  progress: number;
  created_at: string;
  completed_at: string | null;
}

export interface ScanDetail extends ScanSummary {
  sha1: string;
  mime_type: string | null;
  started_at: string | null;
  results: EngineResult[];
}

export interface CreateScanResponse {
  id: string;
  status: ScanStatus;
  engines_requested: number;
  ws_url: string;
}

/* ------------------------------------------------------------------ */
/* Auth token storage                                                 */
/* ------------------------------------------------------------------ */

const TOKEN_KEY = "scanner_token";
export const getToken = () =>
  typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string | null) => {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
};

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const t = getToken();
  return { ...(extra || {}), ...(t ? { Authorization: `Bearer ${t}` } : {}) };
}

async function check<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: string | undefined;
    try {
      detail = (await res.json())?.detail;
    } catch {
      // ignore
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/* ------------------------------------------------------------------ */
/* Endpoints                                                          */
/* ------------------------------------------------------------------ */

export const api = {
  listEngines: () =>
    fetch(`${API_URL}/api/engines`).then((r) => check<EngineInfo[]>(r)),

  createScan: async (
    file: File,
    engineIds: string[] | null,
    onProgress?: (loaded: number, total: number) => void
  ): Promise<CreateScanResponse> => {
    // Use XHR so we can stream upload progress (fetch doesn't support it natively).
    return new Promise((resolve, reject) => {
      const fd = new FormData();
      fd.append("file", file);
      if (engineIds && engineIds.length) fd.append("engines", engineIds.join(","));

      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_URL}/api/scans`);
      const t = getToken();
      if (t) xhr.setRequestHeader("Authorization", `Bearer ${t}`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(e.loaded, e.total);
      };
      xhr.onerror = () => reject(new Error("network error"));
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            reject(e);
          }
        } else {
          let msg = `HTTP ${xhr.status}`;
          try {
            msg = JSON.parse(xhr.responseText).detail || msg;
          } catch {}
          reject(new Error(msg));
        }
      };
      xhr.send(fd);
    });
  },

  getScan: (id: string) =>
    fetch(`${API_URL}/api/scans/${id}`, { headers: authHeaders() }).then((r) =>
      check<ScanDetail>(r)
    ),

  listScans: () =>
    fetch(`${API_URL}/api/scans`, { headers: authHeaders() }).then((r) =>
      check<ScanSummary[]>(r)
    ),

  register: (email: string, password: string) =>
    fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).then((r) => check<{ access_token: string; user: any }>(r)),

  login: (email: string, password: string) =>
    fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }).then((r) => check<{ access_token: string; user: any }>(r)),

  me: () =>
    fetch(`${API_URL}/api/auth/me`, { headers: authHeaders() }).then((r) =>
      r.ok ? r.json() : null
    ),
};
