export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const ACCESS_TOKEN_KEY = "ats_access_token";
const REFRESH_TOKEN_KEY = "ats_refresh_token";
const VIEW_AS_TOKEN_KEY = "ats_view_as_token";
const VIEW_AS_ROLE_KEY = "ats_view_as_role";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message?: string) {
    super(message ?? `Request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  clearViewAsToken();
}

export function getViewAsRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(VIEW_AS_ROLE_KEY);
}

function getViewAsToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(VIEW_AS_TOKEN_KEY);
}

export function setViewAsToken(accessToken: string, roleName: string) {
  localStorage.setItem(VIEW_AS_TOKEN_KEY, accessToken);
  localStorage.setItem(VIEW_AS_ROLE_KEY, roleName);
}

export function clearViewAsToken() {
  localStorage.removeItem(VIEW_AS_TOKEN_KEY);
  localStorage.removeItem(VIEW_AS_ROLE_KEY);
}

/**
 * Auth headers for requests made outside `apiClient` — file downloads that need
 * to read response headers and build a Blob. Mirrors the token precedence used
 * by `request`, so a role-preview session downloads as that role.
 */
export function authHeaders(): HeadersInit {
  const token = getViewAsToken() ?? getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Endpoints where a 401 is the endpoint's own answer ("wrong credentials",
 * "expired reset link") rather than an expired session. The session interceptor
 * must not touch these: refreshing makes no sense, and hard-redirecting to the
 * login page turns a wrong password into an unexplained page reload.
 */
const UNAUTHENTICATED_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout"];

function isUnauthenticatedPath(path: string): boolean {
  return UNAUTHENTICATED_PATHS.some((p) => path === p || path.startsWith(`${p}?`));
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) {
          clearTokens();
          return null;
        }
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return data.access_token as string;
      })
      .catch(() => {
        clearTokens();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  allowRetry = true,
  forceRealToken = false,
): Promise<T> {
  const viewAsToken = forceRealToken ? null : getViewAsToken();
  const token = viewAsToken ?? getAccessToken();
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    // fetch only rejects when the request never got a response: DNS failure,
    // the API being down, a blocked CORS preflight, or mixed content. Reported
    // as an ApiError so callers render it like any other failure rather than
    // falling through to a generic "something went wrong".
    throw new ApiError(0, null, `Could not reach the API at ${API_BASE}. Check your connection.`);
  }

  if (res.status === 401 && allowRetry && !isUnauthenticatedPath(path)) {
    if (viewAsToken) {
      // Preview sessions aren't refreshable — drop back to the real identity.
      clearViewAsToken();
      if (typeof window !== "undefined") window.location.reload();
      throw new ApiError(401, null, "Preview session expired");
    }
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request<T>(path, options, false, forceRealToken);
    }
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/auth/login";
    throw new ApiError(401, null, "Session expired");
  }

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      // response had no JSON body
    }
    const message =
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(res.status, detail, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/**
 * Like `request`, but for list endpoints that report their total row count on
 * the `X-Total-Count` header (see backend `app/core/pagination.py`). Kept
 * separate from `request` rather than changing its return shape, since the
 * vast majority of callers just want the array.
 */
async function requestPage<T>(
  path: string,
  allowRetry = true,
): Promise<{ data: T[]; total: number }> {
  const token = getViewAsToken() ?? getAccessToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { method: "GET", headers });

  if (res.status === 401 && allowRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) return requestPage<T>(path, false);
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/auth/login";
    throw new ApiError(401, null, "Session expired");
  }

  if (!res.ok) {
    throw new ApiError(res.status, null, res.statusText);
  }

  const data = (await res.json()) as T[];
  const totalHeader = res.headers.get("X-Total-Count");
  return { data, total: totalHeader ? Number(totalHeader) : data.length };
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  getPage: <T>(path: string) => requestPage<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData }),
  /** Always authenticates with the real (non-preview) token — for calls that
   * must work even while a view-as preview session is active, like starting
   * a new preview or switching between roles. */
  postAsRealUser: <T>(path: string, body?: unknown) =>
    request<T>(
      path,
      { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined },
      true,
      true,
    ),
};
