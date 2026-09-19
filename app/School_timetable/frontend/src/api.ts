import type { Session } from "./types";

const TOKEN_KEY = "tt.session";
const APP_BASE = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  (APP_BASE.includes("/apps/school-timetable") ? "/apps/school-timetable" : "http://127.0.0.1:8001");

function apiUrl(path: string) {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

function loginPath() {
  return APP_BASE && APP_BASE !== "/" ? `${APP_BASE}/login` : "/login";
}

export function getSession(): Session | null {
  const raw = localStorage.getItem(TOKEN_KEY);
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function setSession(s: Session | null) {
  if (s) localStorage.setItem(TOKEN_KEY, JSON.stringify(s));
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = getSession();
  const headers: Record<string, string> = {
    ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(init.headers as Record<string, string> | undefined),
  };
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
  if (session?.role === "super_admin" && session.school_id) {
    headers["X-School-Id"] = String(session.school_id);
  }
  const res = await fetch(apiUrl(path), { ...init, headers });
  if (res.status === 401) {
    setSession(null);
    if (!path.includes("/auth/login") && !path.includes("/auth/portal-sso")) {
      window.location.href = loginPath();
    }
  }
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail;
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail || data || res.statusText);
    throw new Error(msg);
  }
  return data as T;
}

export async function download(path: string, filename: string) {
  const session = getSession();
  const headers: Record<string, string> = {};
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;
  if (session?.role === "super_admin" && session.school_id) {
    headers["X-School-Id"] = String(session.school_id);
  }
  const res = await fetch(apiUrl(path), { headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Download failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body instanceof FormData ? body : JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
