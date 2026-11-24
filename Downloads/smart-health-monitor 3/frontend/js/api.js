// Thin wrapper around fetch(): adds the auth token and turns errors into exceptions.
const TOKEN_KEY = "shm_token";
export const auth = {
  get token() { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set token(v) { try { v ? localStorage.setItem(TOKEN_KEY, v) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ } },
};

export class ApiError extends Error {
  constructor(message, status, fields) { super(message); this.status = status; this.fields = fields; }
}

async function call(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;
  let res;
  try {
    res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Cannot reach the server. Is it running?", 0);
  }
  if (raw && res.ok) return res;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || "Something went wrong.", res.status, data.fields);
  return data;
}

export const api = {
  schema: () => call("/api/schema"),
  models: () => call("/api/models"),
  doctors: (params) => call("/api/doctors?" + new URLSearchParams(params)),
  report: (payload) => call("/api/report", { method: "POST", body: payload }),
  pdf: (report) => call("/api/report/pdf", { method: "POST", body: report, raw: true }),
  register: (b) => call("/api/auth/register", { method: "POST", body: b }),
  login: (b) => call("/api/auth/login", { method: "POST", body: b }),
  me: () => call("/api/auth/me"),
  history: () => call("/api/history"),
  savedReport: (id) => call("/api/reports/" + id),
  book: (b) => call("/api/appointments", { method: "POST", body: b }),
};
