import api from "@/lib/axios";
import type { CaseDetail, CaseListResp, LlmLogResp } from "./types";

export async function createCase(rawText: string): Promise<{ id: string }> {
  const { data } = await api.post("/cases", { rawText });
  return data;
}

export async function generateCase(caseId: string, force = false): Promise<CaseDetail> {
  // stream=false → backend returns plain JSON instead of SSE.
  const { data } = await api.post<CaseDetail>(
    `/cases/${caseId}/generate?force=${force}&stream=false`,
  );
  return data;
}

export interface StageEvent {
  stage: string;
  label: string;
  index: number;
  total: number;
}

export interface GenerateStreamOptions {
  force?: boolean;
  onStage?: (e: StageEvent) => void;
  signal?: AbortSignal;
}

/**
 * Stream-based generation. Uses fetch + ReadableStream + TextDecoder so we can
 * attach the JWT Authorization header (the native EventSource API cannot).
 *
 * Resolves with the full CaseDetail received in the final `done` event, or
 * rejects with an Error containing the server's message on `error` events,
 * non-2xx responses, or premature stream termination.
 */
export async function generateCaseStream(
  caseId: string,
  { force = false, onStage, signal }: GenerateStreamOptions = {},
): Promise<CaseDetail> {
  const token = localStorage.getItem("token");
  const resp = await fetch(`https://medicalproject-jml5.onrender.com/api/cases/${caseId}/generate?force=${force}`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal,
  });

  if (resp.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!resp.ok || !resp.body) {
    let msg = `Generation failed (${resp.status})`;
    try {
      const data = await resp.json();
      msg = data?.error?.message ?? msg;
    } catch {
      /* not JSON — keep default */
    }
    throw new Error(msg);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let final: CaseDetail | null = null;
  let errMsg: string | null = null;

  const handleFrame = (frame: string) => {
    const { event, data } = parseSseFrame(frame);
    if (!event || data === null) return;
    let payload: unknown;
    try {
      payload = JSON.parse(data);
    } catch {
      return;
    }
    if (event === "stage") {
      onStage?.(payload as StageEvent);
    } else if (event === "done") {
      final = payload as CaseDetail;
    } else if (event === "error") {
      errMsg = (payload as { message?: string })?.message ?? "Generation failed";
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line. Backend emits LF only;
      // also tolerate CRLF in case a proxy rewrites line endings.
      let sep: number;
      while (
        (sep = buffer.indexOf("\n\n")) >= 0 ||
        (sep = buffer.indexOf("\r\n\r\n")) >= 0
      ) {
        const skip = buffer.startsWith("\r\n\r\n", sep) ? 4 : 2;
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + skip);
        handleFrame(frame);
      }
    }
    // Flush trailing bytes / final partial frame, if any.
    buffer += decoder.decode();
    if (buffer.trim()) handleFrame(buffer);
  } finally {
    reader.releaseLock();
  }

  if (errMsg) throw new Error(errMsg);
  if (!final) throw new Error("Stream ended without a 'done' event.");
  return final;
}

function parseSseFrame(frame: string): { event: string | null; data: string | null } {
  let event: string | null = null;
  const dataLines: string[] = [];
  for (const rawLine of frame.split(/\r?\n/)) {
    if (!rawLine || rawLine.startsWith(":")) continue; // skip empty + comment lines
    const colon = rawLine.indexOf(":");
    if (colon < 0) continue;
    const field = rawLine.slice(0, colon);
    let val = rawLine.slice(colon + 1);
    if (val.startsWith(" ")) val = val.slice(1); // SSE: optional single leading space
    if (field === "event") event = val;
    else if (field === "data") dataLines.push(val);
  }
  return { event, data: dataLines.length ? dataLines.join("\n") : null };
}

export async function listCases(page = 1, pageSize = 20): Promise<CaseListResp> {
  const { data } = await api.get<CaseListResp>("/cases", { params: { page, pageSize } });
  return data;
}

export async function getCase(caseId: string): Promise<CaseDetail> {
  const { data } = await api.get<CaseDetail>(`/cases/${caseId}`);
  return data;
}

export async function patchCase(caseId: string, patch: unknown): Promise<CaseDetail> {
  const { data } = await api.patch<CaseDetail>(`/cases/${caseId}`, patch);
  return data;
}

export async function deleteCase(caseId: string): Promise<void> {
  await api.delete(`/cases/${caseId}`);
}

export async function getLlmLog(caseId: string): Promise<LlmLogResp> {
  const { data } = await api.get<LlmLogResp>(`/cases/${caseId}/llm-log`);
  return data;
}
