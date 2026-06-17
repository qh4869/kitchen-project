/**
 * Thin fetch wrapper. All endpoints are relative so the Vite dev proxy
 * (or in production, the reverse proxy) routes them to the FastAPI backend.
 */

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const headers = new Headers(init?.headers);
  let body = init?.body;
  if (init?.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const r = await fetch(path, { ...init, headers, body });
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const err = await r.json();
      detail = err.detail ?? detail;
    } catch {
      // ignore JSON parse error
    }
    throw new ApiError(r.status, detail);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, json?: unknown) =>
    request<T>(path, { method: "POST", json }),
  put: <T>(path: string, json?: unknown) =>
    request<T>(path, { method: "PUT", json }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<T>(path, { method: "POST", body: fd });
  },
};
