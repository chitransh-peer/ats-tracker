const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && allowRetry) {
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

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
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
