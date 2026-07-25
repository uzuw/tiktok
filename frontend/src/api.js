const BASE = import.meta.env.DEV ? "" : "";

async function api(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res;
}

export async function resolveVideo(url) {
  const res = await api("/resolve", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
  return res.json();
}

export function downloadUrl(url, formatId) {
  const params = new URLSearchParams({ url, format_id: formatId });
  return BASE + "/download?" + params.toString();
}

export async function enqueue(url, formatId) {
  const res = await api("/queue", {
    method: "POST",
    body: JSON.stringify({ url, format_id: formatId || "" }),
  });
  return res.json();
}

export async function listQueue() {
  const res = await api("/queue");
  return res.json();
}

export async function getQueueItem(id) {
  const res = await api(`/queue/${id}`);
  return res.json();
}

export async function removeQueueItem(id) {
  await api(`/queue/${id}`, { method: "DELETE" });
}

export async function clearQueue() {
  const res = await api("/queue", { method: "DELETE" });
  return res.json();
}

export async function authStatus() {
  const res = await api("/auth/status");
  return res.json();
}

export async function uploadCookies(text) {
  const res = await api("/auth/cookies", {
    method: "POST",
    body: JSON.stringify({ cookies: text }),
  });
  return res.json();
}

export async function clearCookies() {
  const res = await api("/auth/cookies", { method: "DELETE" });
  return res.json();
}
