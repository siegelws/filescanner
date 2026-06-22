import { WS_URL, type ScanDetail, type EngineResult } from "./api";

export type ScanEvent =
  | { type: "snapshot"; scan: ScanDetail }
  | { type: "started"; scan_id: string }
  | { type: "engine_started"; engine_id: string }
  | { type: "result"; result: EngineResult }
  | { type: "progress"; completed: number; total: number; detections: number }
  | { type: "completed"; scan: ScanDetail }
  | { type: "error"; error: string };

export function openScanSocket(
  scanId: string,
  onEvent: (e: ScanEvent) => void
): () => void {
  const url = `${WS_URL}/api/ws/scans/${scanId}`;
  const ws = new WebSocket(url);

  ws.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data));
    } catch {
      // ignore malformed frames
    }
  };

  ws.onerror = () => onEvent({ type: "error", error: "websocket error" });

  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}
