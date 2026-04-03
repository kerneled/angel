const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export async function fetchSessions() {
  const res = await fetch(`${API_URL}/api/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function fetchSessionDetail(sessionId: string) {
  const res = await fetch(`${API_URL}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

export function getWsUrl(sessionId: string, mode: string): string {
  return `${WS_URL}/ws/${sessionId}/${mode}`;
}

export async function uploadFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}
