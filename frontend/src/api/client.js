const API_BASE = import.meta.env.VITE_API_BASE || "/api";

let unauthorizedHandler = null;

/** Called whenever a non-auth request comes back 401, so the app can show the login screen. */
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

function errorMessage(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{loc: ["body", "field"], msg: "..."}]
    const first = detail[0];
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "";
    return field && field !== "body" ? `${field}: ${first.msg}` : first.msg;
  }
  return `Request failed (${status})`;
}

export async function request(path, { method = "GET", body, query } = {}) {
  let url = `${API_BASE}${path}`;
  if (query) {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") params.set(key, value);
    });
    const text = params.toString();
    if (text) url += `?${text}`;
  }
  const response = await fetch(url, {
    method,
    credentials: "include",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler && !path.startsWith("/auth/")) unauthorizedHandler();
    throw new ApiError(errorMessage(data, response.status), response.status, data);
  }
  return data;
}

export const get = (path, query) => request(path, { query });
export const post = (path, body = {}) => request(path, { method: "POST", body });
export const put = (path, body = {}) => request(path, { method: "PUT", body });
export const del = (path) => request(path, { method: "DELETE" });
