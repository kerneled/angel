function getApiBase(): string {
  if (typeof window === "undefined") return "http://localhost:8030";

  // If explicit env var is set, use it
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl !== "http://localhost:8030") return envUrl;

  // Auto-detect: same host, API port
  const { hostname, protocol } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8030";
  }
  // Via Cloudflare: use the API subdomain
  if (hostname.includes("dogsense.")) {
    return `${protocol}//dogsense-api.eac-bt.com`;
  }
  // LAN IP: use same IP, API port
  return `${protocol}//${hostname}:8030`;
}

function getWsBase(): string {
  if (typeof window === "undefined") return "ws://localhost:8030";

  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl && envUrl !== "ws://localhost:8030") return envUrl;

  const { hostname, protocol } = window.location;
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "ws://localhost:8030";
  }
  if (hostname.includes("dogsense.")) {
    return `${wsProtocol}//dogsense-api.eac-bt.com`;
  }
  return `${wsProtocol}//${hostname}:8030`;
}

export async function fetchSessions() {
  const res = await fetch(`${getApiBase()}/api/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function fetchSessionDetail(sessionId: string) {
  const res = await fetch(`${getApiBase()}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

export function getWsUrl(sessionId: string, mode: string): string {
  return `${getWsBase()}/ws/${sessionId}/${mode}`;
}

export async function uploadFile(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${getApiBase()}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}
